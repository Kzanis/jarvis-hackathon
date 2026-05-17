"""
list_tahoma_scenarios.py — Liste les scènes (actionGroups) stockées dans la TaHoma.

Usage : python scripts/list_tahoma_scenarios.py
"""
from __future__ import annotations

import json
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
        console.print("[red]TAHOMA_LOCAL_IP ou TAHOMA_LOCAL_TOKEN manquant[/red]")
        return 1

    base = f"https://{ip}:{port}/enduser-mobile-web/1/enduserAPI"
    headers = {"Authorization": f"Bearer {token}"}

    # Essai 1 : actionGroups (scènes utilisateur)
    try:
        r = requests.get(f"{base}/actionGroups", headers=headers, verify=False, timeout=10)
        r.raise_for_status()
        scenarios = r.json()
    except Exception as e:
        console.print(f"[yellow]actionGroups KO: {e}[/yellow]")
        scenarios = []

    console.print(f"\n[bold cyan]── {len(scenarios)} scènes TaHoma détectées ──[/bold cyan]\n")

    if scenarios:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Label", style="bold", width=30)
        table.add_column("oid (court)", style="dim", width=14)
        table.add_column("Actions", width=8, justify="right")
        table.add_column("Devices impliqués", width=50)

        for idx, sc in enumerate(scenarios, start=1):
            label = sc.get("label", "?")
            oid = sc.get("oid", "")
            short_oid = oid[:12] + "…" if len(oid) > 13 else oid
            actions = sc.get("actions", [])

            # Liste des labels des devices impliqués (cherche dans cache local si possible)
            urls = [a.get("deviceURL", "").split("/")[-1] for a in actions]
            urls_display = ", ".join(urls[:5])
            if len(urls) > 5:
                urls_display += f"… (+{len(urls) - 5})"
            if len(urls_display) > 48:
                urls_display = urls_display[:48] + "…"

            table.add_row(str(idx), label, short_oid, str(len(actions)), urls_display)

        console.print(table)
        console.print()

    # Essai 2 : exécutions en cours (pour voir si "vacance" tourne)
    try:
        r = requests.get(f"{base}/exec/current", headers=headers, verify=False, timeout=10)
        if r.status_code == 200:
            running = r.json()
            console.print(f"[bold cyan]── {len(running)} exécutions en cours ──[/bold cyan]")
            for run in running:
                label = run.get("description", "?")
                state = run.get("state", "?")
                exec_id = run.get("id", "?")
                console.print(f"  • {label} (état: {state}, id: {exec_id})")
            console.print()
    except Exception as e:
        console.print(f"[dim]exec/current : {e}[/dim]")

    # Sauvegarde brute pour référence
    out_path = ROOT / "config" / "tahoma_scenarios_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)
    console.print(f"[dim]Sauvegarde brute : {out_path}[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
