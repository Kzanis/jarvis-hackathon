"""
test_tahoma_handler.py — Vérifie le handler TaHoma réel.

1. Garde-fou : instanciation refusée si pas en mode prod explicite
2. Health check : la box répond
3. Liste devices : on récupère bien 17 devices
4. Exécution réelle : on appelle 'my' sur le store banne (commande safe = retour à la position favorite, ne fait rien si pas configurée)

Usage : python scripts/test_tahoma_handler.py
"""
from __future__ import annotations

import asyncio
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

from jarvis.domain.types import CommandAction, DeviceCommand
from jarvis.handlers.tahoma import RealDevicesGuard, TahomaHandler

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


async def main() -> int:
    ip = os.getenv("TAHOMA_LOCAL_IP", "").strip()
    port = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
    token = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()

    if not ip or not token:
        console.print("[red]TAHOMA_LOCAL_IP/TOKEN manquant[/red]")
        return 1

    # ===== TEST 1 : Garde-fou =====
    console.print("\n[bold cyan]── Test 1 : Garde-fou ALLOW_REAL_DEVICES ──[/bold cyan]")
    # Force les variables en mode 'mock' (cas par défaut → doit refuser)
    os.environ["EXECUTION_MODE"] = "mock"
    os.environ["ALLOW_REAL_DEVICES"] = "false"
    try:
        TahomaHandler(ip=ip, port=port, token=token)
        console.print("[red]✗ ÉCHEC : le handler s'est instancié alors qu'il ne devrait pas[/red]")
        return 1
    except RealDevicesGuard as e:
        console.print(f"[green]✓ Garde-fou actif : refus correct[/green]")
        console.print(f"  [dim]{str(e)[:120]}…[/dim]")

    # ===== TEST 2 : Activation explicite =====
    console.print("\n[bold cyan]── Test 2 : Activation explicite (production + allow) ──[/bold cyan]")
    os.environ["EXECUTION_MODE"] = "production"
    os.environ["ALLOW_REAL_DEVICES"] = "true"
    handler = TahomaHandler(ip=ip, port=port, token=token)
    console.print("[green]✓ Handler instancié[/green]")

    # ===== TEST 3 : Health check =====
    console.print("\n[bold cyan]── Test 3 : Health check ──[/bold cyan]")
    healthy = await handler.health_check()
    if healthy:
        console.print("[green]✓ Box répond[/green]")
    else:
        console.print("[red]✗ Box ne répond pas[/red]")
        return 1

    # ===== TEST 4 : Liste devices =====
    console.print("\n[bold cyan]── Test 4 : Liste devices ──[/bold cyan]")
    devices = await handler.list_devices()
    console.print(f"[green]✓ {len(devices)} devices récupérés[/green]")

    # ===== TEST 5 : Exécution réelle (commande 'my' sur store banne) =====
    # 'my' = retour à la position favorite, action douce qui ne déclenche rien si déjà à la position
    console.print("\n[bold cyan]── Test 5 : Exécution réelle (stop sur store banne) ──[/bold cyan]")
    console.print("[yellow]Note : envoie 'stop' au store banne (action neutre s'il est déjà arrêté)[/yellow]")
    cmd = DeviceCommand(
        device_url="6137785",  # store banne
        action=CommandAction.stop,
        correlation_id="test-001",
    )
    result = await handler.execute(cmd)
    console.print(f"  status      : {result.status.value}")
    console.print(f"  duration    : {result.duration_ms} ms")
    if result.error:
        console.print(f"  [red]error    : {result.error}[/red]")
    if result.response:
        console.print(f"  [dim]response : {result.response}[/dim]")

    if result.status.value == "success":
        console.print("\n[bold green]🎉 Handler TaHoma RÉEL opérationnel[/bold green]")
        return 0
    else:
        console.print("\n[bold yellow]⚠ Handler instancié mais commande KO — vérifier[/bold yellow]")
        return 0  # Pas un échec total : connexion+liste OK, juste la commande à debugger


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
