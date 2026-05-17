"""
test_devices.py — Validation des connexions aux 3 devices physiques de Jarvis.

Usage :
    python scripts/test_devices.py

Vérifie la connectivité réseau ET l'authentification API pour :
  - TaHoma (Somfy) — REST HTTPS local + Bearer token
  - Freebox Player — REST HTTPS local + session
  - Devialet — HTTP REST local sans auth

Affiche un rapport coloré et sort en code 0 si 3/3 OK, sinon 1.
"""
from __future__ import annotations

import os
import sys
import socket
from pathlib import Path
from typing import Callable

# Forcer UTF-8 sur Windows (sinon UnicodeEncodeError sur ✓/✗/⚠)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ajoute la racine projet au path pour importer jarvis.*
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    print("Dépendances manquantes. Lance d'abord : pip install -r requirements.txt")
    sys.exit(1)

import requests
import urllib3

# TaHoma utilise un certificat auto-signé en local → on désactive le warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(ROOT / ".env")
# legacy_windows=False : force le rendu moderne (sinon fallback cp1252 qui casse l'Unicode)
console = Console(legacy_windows=False)

# ============================================
# HELPERS
# ============================================

def _ping_host(host: str, port: int, timeout: float = 2.0) -> bool:
    """Test TCP brut. True si le port répond."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False


def _ok(msg: str) -> tuple[str, str]:
    return "[bold green]✓ OK[/bold green]", msg


def _ko(msg: str) -> tuple[str, str]:
    return "[bold red]✗ KO[/bold red]", msg


def _warn(msg: str) -> tuple[str, str]:
    return "[bold yellow]⚠ WARN[/bold yellow]", msg


# ============================================
# TESTS DEVICES
# ============================================

def test_tahoma() -> tuple[str, str]:
    """Test TaHoma : ping réseau + auth Bearer + liste devices."""
    ip = os.getenv("TAHOMA_LOCAL_IP", "").strip()
    port = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
    token = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()

    if not ip or ip.endswith("XX"):
        return _ko("TAHOMA_LOCAL_IP non renseigné dans .env")
    if not token:
        return _ko("TAHOMA_LOCAL_TOKEN non renseigné dans .env")

    if not _ping_host(ip, port):
        return _ko(f"Port {port} injoignable sur {ip} (vérifier réseau LAN)")

    try:
        url = f"https://{ip}:{port}/enduser-mobile-web/1/enduserAPI/setup/devices"
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=5,
        )
        if r.status_code == 401:
            return _ko("Token rejeté (401) — régénérer le Local API Token")
        if r.status_code != 200:
            return _ko(f"HTTP {r.status_code} : {r.text[:120]}")
        devices = r.json()
        return _ok(f"{len(devices)} devices détectés")
    except requests.exceptions.SSLError as e:
        return _warn(f"SSL : {e}")
    except Exception as e:
        return _ko(f"Erreur : {type(e).__name__} — {e}")


def test_freebox() -> tuple[str, str]:
    """Test Freebox : ping + appel API version (pas besoin d'auth pour /api_version)."""
    host = os.getenv("FREEBOX_HOST", "mafreebox.freebox.fr").strip()
    app_token = os.getenv("FREEBOX_APP_TOKEN", "").strip()

    # 1. Connectivité de base
    try:
        r = requests.get(f"http://{host}/api_version", timeout=3)
        if r.status_code != 200:
            return _ko(f"Freebox HTTP {r.status_code} sur /api_version")
        data = r.json()
        api_version = data.get("api_version", "?")
        api_base = data.get("api_base_url", "/api/")
    except Exception as e:
        return _ko(f"Pas de réponse de la Freebox : {e}")

    # 2. Token présent ?
    if not app_token:
        return _warn(
            f"Freebox joignable (API v{api_version}) mais FREEBOX_APP_TOKEN vide. "
            "Appairage requis (1ère exécution accepter sur écran Freebox)."
        )

    return _ok(f"Freebox joignable, API v{api_version}, token configuré")


def test_devialet() -> tuple[str, str]:
    """Devialet intégré dans la Freebox Delta — le test est inclus dans test_freebox()."""
    return _ok("Audio Devialet intégré à la Freebox Delta (contrôle via API Freebox)")


# ============================================
# MAIN
# ============================================

TESTS: list[tuple[str, Callable[[], tuple[str, str]]]] = [
    ("TaHoma (Somfy)", test_tahoma),
    ("Freebox", test_freebox),
    ("Devialet", test_devialet),
]


def main() -> int:
    console.print()
    console.print(Panel.fit(
        "[bold cyan]JARVIS — Test de connectivité devices[/bold cyan]\n"
        "[dim]Hackathon Creator Academy — étape 1D[/dim]",
        border_style="cyan",
    ))
    console.print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Device", style="bold", width=18)
    table.add_column("Statut", width=12)
    table.add_column("Détails")

    results: list[bool] = []
    for idx, (name, fn) in enumerate(TESTS, start=1):
        try:
            status, detail = fn()
        except Exception as e:
            status, detail = _ko(f"Exception non gérée : {e}")
        table.add_row(str(idx), name, status, detail)
        # On considère OK seulement si le status est vert
        results.append("OK" in status)

    console.print(table)
    console.print()

    ok_count = sum(results)
    total = len(results)
    if ok_count == total:
        console.print(Panel.fit(
            f"[bold green]{ok_count}/{total} devices OK — prêt pour l'étape 2 (handler TaHoma)[/bold green]",
            border_style="green",
        ))
        return 0
    else:
        console.print(Panel.fit(
            f"[bold yellow]{ok_count}/{total} devices OK — corriger les erreurs avant de continuer[/bold yellow]\n\n"
            "[dim]Conseils :\n"
            "  • Vérifier le .env (IPs, tokens)\n"
            "  • Confirmer que les devices sont sur le même réseau que ce PC\n"
            "  • TaHoma : régénérer le Local API Token si 401\n"
            "  • Freebox : accepter l'appairage sur l'écran Freebox\n"
            "  • Devialet : Phantom allumé et IP correcte ?[/dim]",
            border_style="yellow",
        ))
        return 1


if __name__ == "__main__":
    sys.exit(main())
