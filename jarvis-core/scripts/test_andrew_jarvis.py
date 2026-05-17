"""
test_andrew_jarvis.py — Valide la nouvelle façade TTS avec Andrew (Edge-TTS).

Joue les 4 phrases canoniques majordome.
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

from dotenv import load_dotenv
from rich.console import Console

from jarvis.core.voice import JarvisTTS

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


PHRASES = [
    "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit.",
    "Vous souhaitez bien ouvrir le portail Monsieur ?",
    "Bien Monsieur. Ce sera fait.",
    "Excellente nuit Monsieur. Je veille.",
]


async def main() -> int:
    console.print("\n[bold cyan]── Test final voix Andrew (Edge-TTS, backend par défaut) ──[/bold cyan]\n")

    tts = JarvisTTS()  # Lit TTS_BACKEND et TTS_VOICE_ID depuis .env
    console.print(f"[dim]Backend actif : {tts.name}[/dim]\n")

    out_dir = ROOT / "data" / "andrew_final"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, phrase in enumerate(PHRASES, start=1):
        out = out_dir / f"phrase_{i:02d}.mp3"
        console.print(f"[{i}/{len(PHRASES)}] [italic]\"{phrase}\"[/italic]")
        t0 = time.perf_counter()
        try:
            await tts.synthesize(phrase, out)
            duration = int((time.perf_counter() - t0) * 1000)
            console.print(f"     [green]✓[/green] {duration} ms — {out}")
        except Exception as e:
            console.print(f"     [red]✗ {type(e).__name__} : {e}[/red]")
            return 1

    console.print(f"\n[bold green]✓ 4 phrases générées dans {out_dir}[/bold green]")

    # Lance la première (Bonjour Monsieur)
    first = out_dir / "phrase_01.mp3"
    os.startfile(str(first))  # type: ignore[attr-defined]
    console.print(f"[dim]Lecture de {first.name} lancée…[/dim]\n")

    console.print("[yellow]Pour écouter les autres :[/yellow]")
    for f in sorted(out_dir.glob("*.mp3"))[1:]:
        console.print(f"   start \"\" \"{f}\"")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
