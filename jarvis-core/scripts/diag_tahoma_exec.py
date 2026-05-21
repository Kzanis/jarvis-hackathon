"""
diag_tahoma_exec.py — Diagnostic exécution Somfy pour portail + garage.

Envoie une commande sur le portail (open) puis le garage (close), récupère
l'execId retourné par l'API Overkiz, et **poll l'état d'exécution** pour voir
si le moteur Somfy a réellement bougé (ou si la commande a échoué côté physique).

Usage : python scripts/diag_tahoma_exec.py [open_gate|close_garage|both]
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

IP = os.getenv("TAHOMA_LOCAL_IP", "").strip() or os.getenv("TAHOMA_IP", "").strip()
PORT = int(os.getenv("TAHOMA_LOCAL_PORT", os.getenv("TAHOMA_PORT", "8443")))
TOKEN = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip() or os.getenv("TAHOMA_TOKEN", "").strip()

if not IP or not TOKEN:
    print("ERREUR : TAHOMA_LOCAL_IP / TAHOMA_LOCAL_TOKEN absents du .env")
    sys.exit(1)

BASE = f"https://{IP}:{PORT}/enduser-mobile-web/1/enduserAPI"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

GATE_URL = "rts://<PIN_BOX>/16471272"      # PORTAIL
GARAGE_URL = "io://<PIN_BOX>/881454"       # porte garage


def send_command(device_url: str, command_name: str, label_prefix: str) -> str | None:
    """Envoie une commande, retourne l'execId ou None si échec."""
    payload = {
        "label": f"diag {label_prefix} {command_name}",
        "actions": [
            {
                "deviceURL": device_url,
                "commands": [{"name": command_name, "parameters": []}],
            }
        ],
    }
    print(f"\n>>> POST /exec/apply  device={device_url.split('/')[-1]}  command={command_name!r}")
    r = requests.post(
        f"{BASE}/exec/apply", json=payload, headers=HEADERS, verify=False, timeout=10
    )
    print(f"    HTTP {r.status_code}")
    try:
        body = r.json()
    except Exception:
        print(f"    Body brut : {r.text[:300]}")
        return None
    print(f"    Body : {body}")
    return body.get("execId")


def poll_exec(exec_id: str, max_wait_s: float = 12.0) -> None:
    """Poll l'état d'une exécution toutes les 0.5s jusqu'à fin ou timeout."""
    print(f"\n    Poll /exec/current/{exec_id} (max {max_wait_s}s)")
    deadline = time.time() + max_wait_s
    last_state = None
    while time.time() < deadline:
        r = requests.get(
            f"{BASE}/exec/current/{exec_id}", headers=HEADERS, verify=False, timeout=5
        )
        if r.status_code == 404:
            # plus dans current → soit terminé, soit historisé
            print(f"    [{time.strftime('%H:%M:%S')}] 404 (fini ou archivé)")
            check_history(exec_id)
            return
        try:
            body = r.json()
        except Exception:
            print(f"    [{time.strftime('%H:%M:%S')}] HTTP {r.status_code} body non-JSON")
            time.sleep(0.5)
            continue
        if body is None:
            print(f"    [{time.strftime('%H:%M:%S')}] body=null (execId plus dans current)")
            check_history(exec_id)
            return
        state = body.get("state", "?")
        if state != last_state:
            print(f"    [{time.strftime('%H:%M:%S')}] state={state}  body={body}")
            last_state = state
        if state in ("COMPLETED", "FAILED", "CANCELLED"):
            return
        time.sleep(0.5)
    print(f"    Timeout après {max_wait_s}s sans état final")
    check_history(exec_id)


def check_history(exec_id: str) -> None:
    """Cherche l'exécution dans l'historique pour récupérer l'état final."""
    print(f"    -> Recherche dans /history/executions")
    try:
        r = requests.get(
            f"{BASE}/history/executions", headers=HEADERS, verify=False, timeout=5
        )
        if r.status_code != 200:
            print(f"       HTTP {r.status_code}")
            return
        items = r.json()
        for it in items[:20]:
            if it.get("id") == exec_id or it.get("execId") == exec_id:
                print(f"       MATCH historique : {it}")
                return
        print(f"       Pas trouvé dans les 20 premiers historiques")
    except Exception as e:
        print(f"       Erreur historique : {e}")


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "both"

    if target in ("open_gate", "both"):
        print("=" * 70)
        print("TEST 1/2 — PORTAIL (rts) command=open")
        print("=" * 70)
        exec_id = send_command(GATE_URL, "open", "portail")
        if exec_id:
            poll_exec(exec_id)
        time.sleep(2)

    if target in ("close_garage", "both"):
        print("\n" + "=" * 70)
        print("TEST 2/2 — PORTE GARAGE (io) command=close")
        print("=" * 70)
        exec_id = send_command(GARAGE_URL, "close", "garage")
        if exec_id:
            poll_exec(exec_id)

    print("\nDiagnostic terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
