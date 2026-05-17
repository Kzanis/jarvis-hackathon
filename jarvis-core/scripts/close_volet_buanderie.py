"""
close_volet_buanderie.py — Premier test physique en conditions réelles.

Pipeline complet : Intent → Policy → Orchestrator → TahomaHandler RÉEL → Audit
Le volet buanderie doit physiquement se fermer chez Denis.

Usage : python scripts/close_volet_buanderie.py
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
from rich.panel import Panel

from jarvis.audit.store import SqliteAuditStore
from jarvis.core.orchestrator import Orchestrator
from jarvis.domain.types import (
    CommandAction,
    ConversationContext,
    ExecutionMode,
    Intent,
)
from jarvis.handlers.tahoma import TahomaHandler
from jarvis.policy.engine import PolicyEngine

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


async def main() -> int:
    # Active explicitement le mode production (garde-fou)
    os.environ["EXECUTION_MODE"] = "production"
    os.environ["ALLOW_REAL_DEVICES"] = "true"

    ip = os.getenv("TAHOMA_LOCAL_IP", "").strip()
    port = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
    token = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()

    console.print(Panel.fit(
        "[bold red]TEST PHYSIQUE — Mode PRODUCTION[/bold red]\n"
        "[yellow]Le volet de la buanderie va RÉELLEMENT se fermer.[/yellow]",
        border_style="red",
    ))

    # Wire up
    audit_path = ROOT / "data" / "audit_real.sqlite"
    audit = SqliteAuditStore(audit_path, b"prod-hmac-secret-for-test")

    policy = PolicyEngine()
    handler = TahomaHandler(ip=ip, port=port, token=token)

    url_resolver = {
        "volet_buanderie": "1218264",
    }

    orchestrator = Orchestrator(
        policy=policy,
        handler=handler,
        audit=audit,
        device_url_resolver=url_resolver,
        mode=ExecutionMode.production,
    )

    ctx = ConversationContext()

    # Intent : fermer le volet buanderie
    intent = Intent(
        name="close_shutter",
        action=CommandAction.close,
        target="volet_buanderie",
        confidence=1.0,
        raw_text="Jarvis, ferme le volet de la buanderie",
    )

    console.print("\n[bold cyan]→ Envoi via pipeline complet…[/bold cyan]")
    result = await orchestrator.handle_intent(intent, ctx)

    console.print(f"\n  outcome    : [bold]{result.outcome}[/bold]")
    console.print(f"  decision   : {result.decision.status.value} ({result.decision.effective_sensitivity.value})")
    console.print(f"  reason     : [dim]{result.decision.reason}[/dim]")
    console.print(f"  jarvis dit : [italic cyan]\"{result.speak}\"[/italic cyan]")

    if result.execution:
        console.print(f"  duration   : {result.execution.duration_ms} ms")
        if result.execution.response:
            console.print(f"  [dim]exec_id   : {result.execution.response.get('exec_id', '')}[/dim]")
        if result.execution.error:
            console.print(f"  [red]error    : {result.execution.error}[/red]")

    console.print()
    if result.outcome == "executed" and result.execution and result.execution.status.value == "success":
        console.print(Panel.fit(
            "[bold green]✓ Commande envoyée à la box[/bold green]\n"
            "[yellow]→ Vérifie physiquement que le volet de la buanderie se ferme[/yellow]",
            border_style="green",
        ))
        return 0
    else:
        console.print(Panel.fit(
            "[bold red]✗ Échec[/bold red]",
            border_style="red",
        ))
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
