"""
test_tts_jarvis.py — Teste la voix majordome de Jarvis.

Génère 4 phrases canoniques du PRD, joue chacune, sauve les MP3.

Usage : python scripts/test_tts_jarvis.py
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


PHRASES = [
    "Bonjour Monsieur. J'espère que vous avez passé une excellente nuit.",
    "Vous souhaitez bien ouvrir le portail Monsieur ?",
    "Bien Monsieur. Ce sera fait.",
    "Excellente nuit Monsieur. Je veille.",
]


def main() -> int:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB").strip()

    if not api_key:
        console.print("[red]ELEVENLABS_API_KEY absente du .env[/red]")
        return 1

    console.print(f"[bold cyan]── Test voix Jarvis (voice_id={voice_id[:8]}…) ──[/bold cyan]\n")

    tts = JarvisTTS(api_key=api_key, voice_id=voice_id)

    out_dir = ROOT / "data" / "tts_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, phrase in enumerate(PHRASES, start=1):
        console.print(f"[{i}/{len(PHRASES)}] [italic]\"{phrase}\"[/italic]")
        out = out_dir / f"phrase_{i:02d}.mp3"
        t0 = time.perf_counter()
        try:
            tts.synthesize(phrase, out)
            duration = int((time.perf_counter() - t0) * 1000)
            size_kb = out.stat().st_size / 1024
            console.print(f"   [green]✓[/green] généré en {duration} ms — {size_kb:.1f} KB — {out}")
        except Exception as e:
            console.print(f"   [red]✗[/red] {type(e).__name__} : {e}")
            return 1

    console.print(f"\n[bold green]✓ 4 phrases générées dans {out_dir}[/bold green]")
    console.print("[yellow]→ Joue le premier MP3 pour valider la voix :[/yellow]")
    first = out_dir / "phrase_01.mp3"
    console.print(f"   start \"\" \"{first}\"\n")

    # Joue automatiquement la première sous Windows
    try:
        os.startfile(str(first))  # type: ignore[attr-defined]
        console.print("[dim]Lecture de phrase_01.mp3 lancée…[/dim]")
    except Exception as e:
        console.print(f"[dim]Lecture auto KO : {e}[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
