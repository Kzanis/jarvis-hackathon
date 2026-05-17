"""
demo_pipeline.py — Démonstration du moteur de commande Jarvis en mode mock.

Joue 5 scénarios pour valider :
  1. Commande safe (volume)            → exécution directe
  2. Commande sensible (portail)        → confirmation requise
  3. Confirmation acceptée              → exécution
  4. Commande critique (alarme)         → PIN requis
  5. Système locked + audit chain check

Usage : python scripts/demo_pipeline.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
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
    SensitivityLevel,
)
from jarvis.mocks.tahoma_mock import TahomaMock
from jarvis.policy.engine import PolicyEngine

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


async def main() -> int:
    console.print(Panel.fit(
        "[bold cyan]Jarvis — Démo pipeline (mode mock)[/bold cyan]\n"
        "[dim]Aucun device réel n'est touché.[/dim]",
        border_style="cyan",
    ))

    # Setup
    audit_path = ROOT / "data" / "audit_demo.sqlite"
    if audit_path.exists():
        audit_path.unlink()  # repart de zéro pour la démo
    secret = b"demo-hmac-secret-not-for-prod"
    audit = SqliteAuditStore(audit_path, secret)

    policy = PolicyEngine()
    handler = TahomaMock()

    url_resolver = {
        "portail": "16471272",
        "porte_garage": "881454",
        "alarme_zone_1": "438974",
        "volet_salon": "1454237",
    }

    orchestrator = Orchestrator(
        policy=policy,
        handler=handler,
        audit=audit,
        device_url_resolver=url_resolver,
        mode=ExecutionMode.mock,
    )

    ctx = ConversationContext()

    # ===== Scénario 1 : commande SAFE =====
    console.print("\n[bold green]── Scénario 1 — Commande SAFE (volume) ──[/bold green]")
    intent = Intent(
        name="set_volume",
        action=CommandAction.set_volume,
        target="freebox",
        params={"value": 45},
        confidence=0.95,
        raw_text="Jarvis, monte le son à 45",
    )
    result = await orchestrator.handle_intent(intent, ctx, now=_daytime())
    _print_result(result)

    # ===== Scénario 2 : commande SENSIBLE (portail jour) =====
    console.print("\n[bold yellow]── Scénario 2 — Commande SENSIBLE (portail jour) ──[/bold yellow]")
    intent_gate = Intent(
        name="open_gate",
        action=CommandAction.open,
        target="portail",
        confidence=0.95,
        raw_text="Jarvis, ouvre le portail",
    )
    result = await orchestrator.handle_intent(intent_gate, ctx, now=_daytime())
    _print_result(result)

    # ===== Scénario 3 : confirmation acceptée =====
    console.print("\n[bold green]── Scénario 3 — Denis répond 'oui' ──[/bold green]")
    result = await orchestrator.confirm(ctx, "oui Jarvis", now=_daytime())
    _print_result(result)
    console.print(f"  [dim]Appels handler TaHoma mock : {len(handler.calls)}[/dim]")
    console.print(f"  [dim]Dernier appel : {handler.calls[-1] if handler.calls else 'aucun'}[/dim]")

    # ===== Scénario 4 : commande CRITIQUE (alarme) =====
    console.print("\n[bold red]── Scénario 4 — Commande CRITIQUE (alarme) ──[/bold red]")
    intent_alarm = Intent(
        name="disarm_alarm",
        action=CommandAction.disarm,
        target="alarme_zone_1",
        confidence=0.95,
        raw_text="Jarvis, désactive l'alarme",
    )
    result = await orchestrator.handle_intent(intent_alarm, ctx, now=_daytime())
    _print_result(result)

    # ===== Scénario 5 : ouverture portail la NUIT (élévation auto) =====
    console.print("\n[bold red]── Scénario 5 — Portail la NUIT (élévation auto sensible → critique) ──[/bold red]")
    ctx_night = ConversationContext()  # contexte neuf
    result = await orchestrator.handle_intent(intent_gate, ctx_night, now=_nighttime())
    _print_result(result)

    # ===== Vérification audit chain =====
    console.print("\n[bold cyan]── Vérification chaîne d'audit ──[/bold cyan]")
    events = audit.recent(100)
    console.print(f"  [dim]{len(events)} événements audit enregistrés[/dim]")
    chain_ok = audit.verify_chain()
    if chain_ok:
        console.print("  [green]✓ Chaîne HMAC intègre (aucune altération détectée)[/green]")
    else:
        console.print("  [red]✗ CHAÎNE CORROMPUE[/red]")

    console.print()
    console.print(Panel.fit(
        f"[bold green]Pipeline OK[/bold green]\n"
        f"Mode : {ExecutionMode.mock.value}\n"
        f"Appels handler : {len(handler.calls)}\n"
        f"Événements audit : {len(events)}\n"
        f"Chain intégrité : {'OK' if chain_ok else 'KO'}",
        border_style="green",
    ))
    return 0


def _print_result(result):
    console.print(f"  outcome    : [bold]{result.outcome}[/bold]")
    console.print(f"  decision   : {result.decision.status.value} ({result.decision.effective_sensitivity.value})")
    console.print(f"  reason     : [dim]{result.decision.reason}[/dim]")
    console.print(f"  jarvis dit : [italic cyan]\"{result.speak}\"[/italic cyan]")


def _daytime() -> datetime:
    return datetime(2026, 5, 14, 14, 30, 0)


def _nighttime() -> datetime:
    return datetime(2026, 5, 14, 23, 30, 0)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
