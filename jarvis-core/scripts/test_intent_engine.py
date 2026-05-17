"""
test_intent_engine.py — Vérifie que Claude reconnaît bien les synonymes.

Joue 8 phrases avec des variations de vocabulaire pour valider le mapping.
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
from rich.table import Table

from jarvis.core.intent_engine import IntentEngine

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


TEST_PHRASES = [
    ("Jarvis, ferme le volet de la buanderie", "volet_buanderie", "close"),
    ("Tu peux baisser le rideau de la buanderie ?", "volet_buanderie", "close"),
    ("Ouvre le store de la cuisine", "volet_cuisine", "open"),
    ("Jarvis, ouvre le portail", "portail", "open"),
    ("Ferme la barrière s'il te plaît", "portail", "close"),
    ("Joris, je pars", "je_pars", "close"),
    ("Active l'alarme zone 1", "alarme_zone_1", "arm"),
    ("Quel temps fait-il dehors ?", None, "stop"),  # Doit être unknown
]


async def main() -> int:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY manquante[/red]")
        return 1

    engine = IntentEngine(
        api_key=api_key,
        settings_path=ROOT / "config" / "settings.yaml",
    )

    console.print("\n[bold cyan]── Test IntentEngine — reconnaissance synonymes ──[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Phrase", style="bold", width=45)
    table.add_column("Target attendu", width=18)
    table.add_column("Target obtenu", width=18)
    table.add_column("Action", width=10)
    table.add_column("Conf.", justify="right", width=6)
    table.add_column("OK", width=4)

    ok_count = 0
    for phrase, expected_target, expected_action in TEST_PHRASES:
        try:
            intent = await engine.classify(phrase)
            ok = (intent.target == expected_target) and (intent.action.value == expected_action)
            mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
            if ok:
                ok_count += 1
            table.add_row(
                phrase[:43] + ("…" if len(phrase) > 43 else ""),
                str(expected_target),
                str(intent.target),
                intent.action.value,
                f"{intent.confidence:.2f}",
                mark,
            )
        except Exception as e:
            table.add_row(phrase[:43], str(expected_target), f"ERREUR: {type(e).__name__}", "-", "-", "[red]✗[/red]")

    console.print(table)
    console.print(f"\n[bold]{ok_count}/{len(TEST_PHRASES)} tests passés[/bold]")
    return 0 if ok_count == len(TEST_PHRASES) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
