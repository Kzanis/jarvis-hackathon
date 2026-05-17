"""
bench_latency.py — Mesure la latence après les 3 optimisations.

Fait 3 commandes 'stop' sur 3 volets (action neutre, pas de mouvement physique).
On compare :
  - Temps perçu (réponse Jarvis "Bien Monsieur" → fin de phrase)
  - Temps d'exécution arrière-plan (durée API réelle)
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
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
    ip = os.getenv("TAHOMA_LOCAL_IP", "").strip()
    port = int(os.getenv("TAHOMA_LOCAL_PORT", "8443"))
    token = os.getenv("TAHOMA_LOCAL_TOKEN", "").strip()

    audit = SqliteAuditStore(ROOT / "data" / "audit_bench.sqlite", b"bench")
    policy = PolicyEngine()
    handler = TahomaHandler(ip=ip, port=port, token=token)

    url_resolver = {
        "volet_buanderie": "1218264",
        "volet_chambre": "1348289",
        "volet_bureau": "5922177",
    }
    orchestrator = Orchestrator(policy, handler, audit, url_resolver, ExecutionMode.production)
    ctx = ConversationContext()

    # Pré-charge le catalogue (premier appel = chargement cache URL)
    console.print("[dim]Pré-chargement du catalogue devices…[/dim]")
    await handler.list_devices()

    # ===== 3 commandes 'stop' successives =====
    console.print("\n[bold cyan]── Bench : 3 commandes 'stop' (perception utilisateur) ──[/bold cyan]\n")
    targets = ["volet_buanderie", "volet_chambre", "volet_bureau"]
    perceived_times = []
    for i, target in enumerate(targets, start=1):
        intent = Intent(
            name="stop_shutter",
            action=CommandAction.stop,
            target=target,
            confidence=1.0,
        )
        t0 = time.perf_counter()
        result = await orchestrator.handle_intent(intent, ctx)
        t1 = time.perf_counter()
        perceived = int((t1 - t0) * 1000)
        perceived_times.append(perceived)
        console.print(f"  [{i}] {target:25s} → perception : [bold green]{perceived:4d} ms[/bold green]  | jarvis : \"{result.speak}\"")

    # Attendre que les commandes en arrière-plan finissent
    await asyncio.sleep(3)
    await handler.aclose()

    avg = sum(perceived_times) // len(perceived_times)
    console.print(f"\n  [bold]Moyenne perception : {avg} ms[/bold] (avant optim : ~1017 ms)")
    if avg < 300:
        console.print("  [bold green]🎉 Objectif atteint (< 300 ms perçu)[/bold green]")
    else:
        console.print(f"  [yellow]⚠ Encore au-dessus de 300 ms[/yellow]")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
