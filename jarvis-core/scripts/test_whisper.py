"""
test_whisper.py — Enregistre 5 secondes au micro et transcrit avec Whisper.

Usage : python scripts/test_whisper.py
"""
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

from jarvis.core.stt import WhisperSTT, record_microphone

console = Console(legacy_windows=False)


async def main() -> int:
    console.print("[bold cyan]── Test Whisper STT ──[/bold cyan]\n")

    console.print("[yellow]Chargement modèle Whisper 'small' (peut prendre 30s la 1ère fois)…[/yellow]")
    stt = WhisperSTT(model_size="small", language="fr")
    console.print("[green]✓ Modèle chargé[/green]\n")

    console.print("[bold red]🎙️  Parlez maintenant pendant 5 secondes…[/bold red]")
    console.print('[dim]Suggestion : "Jarvis, ferme le volet de la buanderie"[/dim]\n')

    audio = record_microphone(duration_seconds=5.0)
    console.print("[green]✓ Enregistrement terminé[/green]\n")

    console.print("[yellow]Transcription en cours…[/yellow]")
    text = await stt.transcribe_array(audio)

    console.print(f"\n[bold green]📝 Transcription :[/bold green]")
    console.print(f'[bold]"{text}"[/bold]\n')

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
