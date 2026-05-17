"""
list_tahoma_devices.py — Liste détaillée des devices TaHoma pour mapping vocal.

Usage :
    python scripts/list_tahoma_devices.py

Sortie : tableau avec label, type, état, commandes disponibles.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


def main() -> int:
    ip = os.getenv("TAHOMA_LOCAL_IP", "").strip()
    port = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
    token = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()

    if not ip or not token:
        console.print("[red]TAHOMA_LOCAL_IP ou TAHOMA_LOCAL_TOKEN manquant dans .env[/red]")
        return 1

    url = f"https://{ip}:{port}/enduser-mobile-web/1/enduserAPI/setup/devices"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
            timeout=10,
        )
        r.raise_for_status()
        devices = r.json()
    except Exception as e:
        console.print(f"[red]Erreur API TaHoma : {e}[/red]")
        return 1

    console.print(f"\n[bold cyan]── {len(devices)} devices TaHoma détectés ──[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Label", style="bold", width=28)
    table.add_column("Type", width=14)
    table.add_column("URL (id court)", style="dim", width=24)
    table.add_column("Commandes principales", width=40)

    for idx, dev in enumerate(devices, start=1):
        label = dev.get("label", "?")
        device_url = dev.get("deviceURL", "")
        short_url = device_url.split("/")[-1] if "/" in device_url else device_url
        if len(short_url) > 22:
            short_url = short_url[:22] + "…"

        # Type : on prend le widget ou la définition
        widget = dev.get("widget", "")
        ui_class = dev.get("uiClass", "")
        type_str = widget or ui_class or "?"
        if len(type_str) > 12:
            type_str = type_str[:12] + "…"

        # Commandes disponibles (extrait commandName)
        commands = dev.get("definition", {}).get("commands", [])
        cmd_names = [c.get("commandName", "") for c in commands]
        # On garde les commandes les plus utiles
        useful = [c for c in cmd_names if c in (
            "open", "close", "stop", "setClosure", "my",
            "on", "off", "setIntensity",
            "arm", "disarm", "alarmZoneOn", "alarmZoneOff",
            "cycle",
        )]
        cmd_display = ", ".join(useful[:5]) if useful else ", ".join(cmd_names[:3])
        if len(cmd_display) > 38:
            cmd_display = cmd_display[:38] + "…"

        table.add_row(str(idx), label, type_str, short_url, cmd_display)

    console.print(table)
    console.print()

    # Résumé par type
    types_count: dict[str, int] = {}
    for dev in devices:
        t = dev.get("uiClass", "Other")
        types_count[t] = types_count.get(t, 0) + 1
    console.print("[bold cyan]── Résumé par type ──[/bold cyan]")
    for t, n in sorted(types_count.items(), key=lambda x: -x[1]):
        console.print(f"  • {t}: {n}")
    console.print()

    # Sauvegarde JSON brut pour référence
    out_path = ROOT / "config" / "tahoma_devices_raw.json"
    import json
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)
    console.print(f"[dim]Sauvegarde brute : {out_path}[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
