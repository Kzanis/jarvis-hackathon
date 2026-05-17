"""
demo_volet_buanderie.py — Démo live : ouvrir le volet buanderie puis le refermer.

Garantit un mouvement physique visible pour un public.
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

os.environ["EXECUTION_MODE"] = "production"
os.environ["ALLOW_REAL_DEVICES"] = "true"

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from jarvis.audit.store import SqliteAuditStore
from jarvis.core.orchestrator import Orchestrator
from jarvis.core.voice import JarvisTTS
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
    ip = os.getenv("TAHOMA_LOCAL_IP", "").strip()
    port = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
    token = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()

    console.print(Panel.fit(
        "[bold red]DÉMO LIVE — Volet buanderie[/bold red]\n"
        "[yellow]1. Ouverture\n2. Pause 10 secondes\n3. Fermeture[/yellow]",
        border_style="red",
    ))

    audit = SqliteAuditStore(ROOT / "data" / "audit_demo_live.sqlite", b"demo")
    policy = PolicyEngine()
    handler = TahomaHandler(ip=ip, port=port, token=token)
    tts = JarvisTTS()

    url_resolver = {"volet_buanderie": "1218264"}
    orchestrator = Orchestrator(
        policy=policy, handler=handler, audit=audit,
        device_url_resolver=url_resolver, mode=ExecutionMode.production,
    )

    ctx = ConversationContext()

    # === Phase 1 : Ouverture ===
    console.print("\n[bold green]→ Phase 1 : Ouverture du volet buanderie[/bold green]")
    intent_open = Intent(
        name="open_shutter",
        action=CommandAction.open,
        target="volet_buanderie",
        confidence=1.0,
        raw_text="Jarvis, ouvre le volet de la buanderie",
    )
    result = await orchestrator.handle_intent(intent_open, ctx)
    console.print(f"   Jarvis dit : [italic cyan]\"{result.speak}\"[/italic cyan]")

    # Voix Jarvis annonce l'ouverture
    cue_open = ROOT / "data" / "cue_demo_open.mp3"
    if not cue_open.exists():
        await tts.synthesize("Bien Monsieur. J'ouvre le volet de la buanderie.", cue_open)
    os.startfile(str(cue_open))  # type: ignore[attr-defined]

    # Attente que le volet monte
    console.print("[dim]Attente 10 secondes que le volet monte…[/dim]")
    for i in range(10, 0, -1):
        print(f"\r   ⏱️  {i} s ", end="", flush=True)
        await asyncio.sleep(1)
    print()

    # === Phase 2 : Fermeture ===
    console.print("\n[bold yellow]→ Phase 2 : Fermeture du volet buanderie[/bold yellow]")
    intent_close = Intent(
        name="close_shutter",
        action=CommandAction.close,
        target="volet_buanderie",
        confidence=1.0,
        raw_text="Jarvis, ferme le volet de la buanderie",
    )
    result = await orchestrator.handle_intent(intent_close, ctx)
    console.print(f"   Jarvis dit : [italic cyan]\"{result.speak}\"[/italic cyan]")

    cue_close = ROOT / "data" / "cue_demo_close.mp3"
    if not cue_close.exists():
        await tts.synthesize("Bien Monsieur. Je referme le volet.", cue_close)
    os.startfile(str(cue_close))  # type: ignore[attr-defined]

    await asyncio.sleep(2)
    await handler.aclose()

    console.print()
    console.print(Panel.fit(
        "[bold green]✓ Démo terminée[/bold green]",
        border_style="green",
    ))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
