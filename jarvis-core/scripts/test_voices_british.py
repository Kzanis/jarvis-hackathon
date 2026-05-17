"""
test_voices_british.py — Compare 3 voix britanniques pour Jarvis.

Génère la même phrase "Bonjour Monsieur" avec 3 voix candidates.
Tu écoutes, tu choisis celle que tu préfères.
"""
from __future__ import annotations

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


# 3 candidats britanniques chez ElevenLabs
VOICES = [
    ("George",  "JBFqnCBsd6RMkjVDRZzb", "British, mature, warm — style Alfred Pennyworth"),
    ("Daniel",  "onwK4e9ZLuTAKqWW03F9", "British news presenter — style J.A.R.V.I.S. classique"),
    ("Brian",   "nPczCjzI2devNBz1zQrb", "British, deep — voix grave assurée"),
]

PHRASE = (
    "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit. "
    "Permettez-moi de vous présenter votre journée."
)


def main() -> int:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        console.print("[red]ELEVENLABS_API_KEY absente[/red]")
        return 1

    out_dir = ROOT / "data" / "voice_compare"
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]── Comparatif 3 voix britanniques ──[/bold cyan]\n")

    for name, voice_id, description in VOICES:
        console.print(f"[bold]{name}[/bold] [dim]({description})[/dim]")
        tts = JarvisTTS(api_key=api_key, voice_id=voice_id)
        out = out_dir / f"{name.lower()}.mp3"
        t0 = time.perf_counter()
        try:
            tts.synthesize(PHRASE, out)
            duration = int((time.perf_counter() - t0) * 1000)
            console.print(f"   [green]✓[/green] {duration} ms — {out}")
        except Exception as e:
            console.print(f"   [red]✗ {type(e).__name__} : {e}[/red]")

    console.print(f"\n[bold yellow]→ Écoute les 3 :[/bold yellow]")
    for name, _, _ in VOICES:
        console.print(f"   start \"\" \"{out_dir / f'{name.lower()}.mp3'}\"")

    # Lance le premier (George) automatiquement
    first = out_dir / "george.mp3"
    if first.exists():
        os.startfile(str(first))  # type: ignore[attr-defined]
        console.print(f"\n[dim]Lecture de {first.name} (George) lancée…[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
