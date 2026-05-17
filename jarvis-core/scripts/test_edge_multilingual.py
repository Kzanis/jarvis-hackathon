"""
test_edge_multilingual.py — Voix Multilingual Microsoft (anglo-saxonnes parlant français nativement).

Ces voix gèrent le français avec leur accent anglais natif → effet majordome british parfait.
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

import edge_tts
from rich.console import Console

console = Console(legacy_windows=False)


# Voix Microsoft Neural Multilingual masculines
# Ces voix prononcent correctement le français avec leur accent natif anglo-saxon
CANDIDATES = [
    ("en-US-AndrewMultilingualNeural",   "Andrew",   "US Multilingual, accent américain sur le français"),
    ("en-US-BrianMultilingualNeural",    "Brian-ML", "US Multilingual, ton conversationnel"),
    ("en-US-AdamMultilingualNeural",     "Adam-ML",  "US Multilingual, voix grave"),
    ("en-GB-AdaMultilingualNeural",      "Ada",      "UK Multilingual — à tester"),
    ("en-US-DerekMultilingualNeural",    "Derek",    "US Multilingual"),
    ("en-US-DustinMultilingualNeural",   "Dustin",   "US Multilingual"),
    ("en-US-LewisMultilingualNeural",    "Lewis",    "US Multilingual"),
    ("en-US-SamuelMultilingualNeural",   "Samuel",   "US Multilingual"),
]

PHRASE = (
    "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit. "
    "Permettez-moi de vous présenter votre journée."
)


async def synthesize(voice_name: str, text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(str(out_path))


async def main() -> int:
    out_dir = ROOT / "data" / "edge_multilingual"
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold cyan]── Voix Multilingual : anglo-saxons parlant français ──[/bold cyan]\n")

    results = []
    for i, (voice_id, name, desc) in enumerate(CANDIDATES, start=1):
        out = out_dir / f"{i:02d}_{name.lower().replace('-', '_')}.mp3"
        console.print(f"[{i}/{len(CANDIDATES)}] [bold]{name}[/bold] [dim]({desc})[/dim]")
        try:
            t0 = time.perf_counter()
            await synthesize(voice_id, PHRASE, out)
            duration = int((time.perf_counter() - t0) * 1000)
            size_kb = out.stat().st_size / 1024
            console.print(f"     [green]✓[/green] {duration} ms — {size_kb:.1f} KB")
            results.append(out)
        except Exception as e:
            err = str(e)[:80]
            console.print(f"     [red]✗ {type(e).__name__} : {err}[/red]")

    console.print(f"\n[bold green]{len(results)}/{len(CANDIDATES)} voix générées dans {out_dir}[/bold green]")
    console.print("\n[bold yellow]→ Écoute-les :[/bold yellow]")
    for f in sorted(out_dir.glob("*.mp3")):
        console.print(f"   start \"\" \"{f}\"")

    if results:
        os.startfile(str(sorted(results)[0]))  # type: ignore[attr-defined]
        console.print(f"\n[dim]Lecture de {sorted(results)[0].name} lancée…[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
