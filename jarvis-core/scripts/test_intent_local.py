"""Test IntentEngineLocal — fuzzy matching gratuit."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.table import Table

from jarvis.core.intent_engine_local import IntentEngineLocal

console = Console(legacy_windows=False)


TESTS = [
    ("Jarvis, ferme le volet de la buanderie", "volet_buanderie", "close"),
    ("Tu peux baisser le rideau de la buanderie ?", "volet_buanderie", "close"),
    ("Ouvre le store de la cuisine", "volet_cuisine", "open"),
    ("Jarvis, ouvre le portail", "portail", "open"),
    ("Ferme la barrière s'il te plaît", "portail", "close"),
    ("Joris, je pars", "je_pars", "close"),
    ("Active l'alarme zone 1", "alarme_zone_1", "arm"),
    ("Quel temps fait-il dehors ?", None, "stop"),
    ("Ferme le rideau du salon", "volet_salon", "close"),
    ("Bonjour Jarvis !", "bonjour", "open"),
]


async def main() -> int:
    engine = IntentEngineLocal(ROOT / "config" / "settings.yaml")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Phrase", style="bold", width=42)
    table.add_column("Attendu", width=16)
    table.add_column("Obtenu", width=16)
    table.add_column("Action", width=8)
    table.add_column("Conf.", justify="right", width=6)
    table.add_column("OK", width=4)

    ok_count = 0
    for phrase, expected_target, expected_action in TESTS:
        intent = await engine.classify(phrase)
        ok = (intent.target == expected_target) and (intent.action.value == expected_action)
        if ok:
            ok_count += 1
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(
            phrase[:40] + ("…" if len(phrase) > 40 else ""),
            str(expected_target)[:14],
            str(intent.target)[:14],
            intent.action.value,
            f"{intent.confidence:.2f}",
            mark,
        )

    console.print(table)
    console.print(f"\n[bold]{ok_count}/{len(TESTS)} tests passés[/bold]")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
