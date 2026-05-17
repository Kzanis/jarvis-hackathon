"""
test_edge_tts_british.py — Teste 5 voix UK Neural gratuites (Microsoft Edge-TTS).

100% gratuit, illimité, pas de clé API.
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


# Voix UK Neural masculines (Microsoft Azure Neural via Edge-TTS gratuit)
VOICES = [
    ("en-GB-RyanNeural",   "Ryan",   "Voix masculine UK Neural, posée"),
    ("en-GB-ThomasNeural", "Thomas", "Voix masculine UK Neural, calme et chaleureuse"),
    ("en-GB-EthanNeural",  "Ethan",  "Voix masculine UK Neural, jeune"),
    ("en-GB-NoahNeural",   "Noah",   "Voix masculine UK Neural"),
    ("en-GB-ElliotNeural", "Elliot", "Voix masculine UK Neural"),
]

PHRASE = (
    "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit. "
    "Permettez-moi de vous présenter votre journée."
)


async def synthesize(voice_name: str, text: str, out_path: Path, rate: str = "+0%", pitch: str = "+0Hz") -> None:
    communicate = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))


async def main() -> int:
    out_dir = ROOT / "data" / "edge_tts_british"
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold cyan]── Test 5 voix UK Neural (Edge-TTS, 100% gratuit) ──[/bold cyan]\n")

    for i, (voice_id, name, desc) in enumerate(VOICES, start=1):
        out = out_dir / f"{i:02d}_{name.lower()}.mp3"
        console.print(f"[{i}/{len(VOICES)}] [bold]{name}[/bold] [dim]({desc})[/dim]")
        try:
            t0 = time.perf_counter()
            await synthesize(voice_id, PHRASE, out)
            duration = int((time.perf_counter() - t0) * 1000)
            size_kb = out.stat().st_size / 1024
            console.print(f"     [green]✓[/green] {duration} ms — {size_kb:.1f} KB — {out.name}")
        except Exception as e:
            console.print(f"     [red]✗ {type(e).__name__} : {e}[/red]")

    console.print(f"\n[bold green]✓ Échantillons dans {out_dir}[/bold green]")
    console.print("\n[bold yellow]→ Écoute-les dans l'ordre :[/bold yellow]")
    for f in sorted(out_dir.glob("*.mp3")):
        console.print(f"   start \"\" \"{f}\"")

    first = sorted(out_dir.glob("*.mp3"))
    if first:
        os.startfile(str(first[0]))  # type: ignore[attr-defined]
        console.print(f"\n[dim]Lecture de {first[0].name} (Ryan) lancée…[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
