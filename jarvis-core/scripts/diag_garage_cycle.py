"""diag_garage_cycle.py — Test contrôlé de la porte de garage via le handler patché.

Valide en réel : le câblage close_garage + le mouvement physique + le polling
d'état d'exécution ajouté dans TahomaHandler.

Usage :
    python scripts/diag_garage_cycle.py state   # lecture seule (ne bouge pas)
    python scripts/diag_garage_cycle.py open
    python scripts/diag_garage_cycle.py close
    python scripts/diag_garage_cycle.py cycle    # ouvre, attend, ferme (observation Denis)
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import requests
import urllib3
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from jarvis.domain.types import CommandAction, DeviceCommand  # noqa: E402
from jarvis.handlers.tahoma import TahomaHandler  # noqa: E402

IP = os.getenv("TAHOMA_LOCAL_IP", "").strip()
PORT = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
TOKEN = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()
GARAGE_URL = "io://<PIN_BOX>/881454"
BASE = f"https://{IP}:{PORT}/enduser-mobile-web/1/enduserAPI"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def read_state() -> None:
    r = requests.get(f"{BASE}/setup/devices", headers=HEADERS, verify=False, timeout=10)
    r.raise_for_status()
    for d in r.json():
        if d.get("deviceURL") == GARAGE_URL:
            states = {s["name"]: s.get("value") for s in d.get("states", [])}
            closure = states.get("core:ClosureState")
            openclose = states.get("core:OpenClosedUnknownState")
            print(f"  Garage : ClosureState={closure}  OpenClosedUnknownState={openclose!r}")
            return
    print("  Garage introuvable dans le catalogue.")


async def send(action: CommandAction) -> None:
    os.environ.setdefault("EXECUTION_MODE", "production")
    os.environ.setdefault("ALLOW_REAL_DEVICES", "true")
    h = TahomaHandler(ip=IP, port=PORT, token=TOKEN)
    cmd = DeviceCommand(device_url=GARAGE_URL, action=action, params={}, correlation_id="diag-garage")
    print(f"\n>>> {action.value} garage…")
    res = await h.execute(cmd)
    print(f"    status={res.status.value}  exec_state={res.response.get('exec_state')}  "
          f"durée={res.duration_ms}ms")
    if res.error:
        print(f"    detail : {res.error}")
    await h.aclose()


def send_raw(command_name: str, params: list | None = None) -> None:
    """Envoie une commande brute à la box et poll /exec/current pour voir l'état réel."""
    params = params or []
    payload = {
        "label": f"diag garage {command_name}",
        "actions": [{"deviceURL": GARAGE_URL, "commands": [{"name": command_name, "parameters": params}]}],
    }
    print(f"\n>>> RAW {command_name}{params} sur garage…")
    r = requests.post(f"{BASE}/exec/apply", json=payload, headers=HEADERS, verify=False, timeout=10)
    print(f"    HTTP {r.status_code}  body={r.text[:200]}")
    try:
        exec_id = r.json().get("execId")
    except Exception:
        exec_id = None
    if not exec_id:
        return
    deadline = time.time() + 12
    last = None
    while time.time() < deadline:
        rr = requests.get(f"{BASE}/exec/current/{exec_id}", headers=HEADERS, verify=False, timeout=5)
        if rr.status_code == 404:
            print(f"    [{time.strftime('%H:%M:%S')}] /exec/current 404 (fini ou jamais suivi)")
            break
        try:
            body = rr.json()
        except Exception:
            body = None
        st = (body or {}).get("state") if body else None
        if st != last:
            print(f"    [{time.strftime('%H:%M:%S')}] state={st} body={body}")
            last = st
        if st in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(0.5)


async def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "state"
    print(f"État initial du garage :")
    read_state()

    if target == "state":
        return 0
    if target == "raw":
        name = sys.argv[2]
        params = [int(x) if x.lstrip('-').isdigit() else x for x in sys.argv[3:]]
        send_raw(name, params)
        time.sleep(8)
        print("\nÉtat final du garage :")
        read_state()
        return 0
    if target == "open":
        await send(CommandAction.open)
    elif target == "close":
        await send(CommandAction.close)
    elif target == "cycle":
        await send(CommandAction.open)
        print("\n    …pause 8s (observe la porte s'ouvrir)…")
        time.sleep(8)
        await send(CommandAction.close)
    else:
        print(f"Cible inconnue : {target!r}")
        return 1

    print("\nÉtat final du garage :")
    read_state()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
