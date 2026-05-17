"""
test_whisper_v3.py — Whisper + cues Jarvis + GAIN LOGICIEL ×30 pour compenser un micro bas.

Si le micro PC capte trop faible (vs dictée Windows qui a AGC),
on amplifie le signal numériquement avant de l'envoyer à Whisper.
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

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from rich.console import Console

from jarvis.core.stt import WhisperSTT
from jarvis.core.voice import JarvisTTS

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


GAIN = 100.0  # Multiplicateur du signal (compense un micro très bas)


async def main() -> int:
    console.print("[bold cyan]── Whisper v3 — avec gain logiciel ×30 ──[/bold cyan]\n")

    tts = JarvisTTS()
    console.print("[yellow]Chargement Whisper…[/yellow]")
    stt = WhisperSTT(model_size="small", language="fr")
    console.print("[green]✓ Whisper prêt[/green]\n")

    # Cues audio
    cue_start = ROOT / "data" / "cue_start.mp3"
    cue_end = ROOT / "data" / "cue_end.mp3"
    if not cue_start.exists():
        await tts.synthesize("À vous Monsieur.", cue_start)
    if not cue_end.exists():
        await tts.synthesize("Merci Monsieur.", cue_end)

    # Cue de démarrage
    console.print("[bold cyan]🔊 Écoute le bip de démarrage…[/bold cyan]")
    os.startfile(str(cue_start))  # type: ignore[attr-defined]
    await asyncio.sleep(2.5)

    # Enregistrement 7s à 48 kHz (natif WASAPI), device par défaut
    duration = 7.0
    native_rate = 48000
    target_rate = 16000
    console.print(f"[bold red]🎙️  PARLE MAINTENANT pendant {int(duration)} secondes (micro par défaut Windows)[/bold red]")
    console.print('[dim]Dis : "Jarvis ferme le volet de la buanderie"[/dim]\n')

    audio_native = sd.rec(
        int(duration * native_rate),
        samplerate=native_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    audio_native = audio_native.flatten()

    # Cue de fin
    os.startfile(str(cue_end))  # type: ignore[attr-defined]

    # Statistiques AVANT gain
    rms_before = float(np.sqrt(np.mean(audio_native**2)))
    peak_before = float(np.max(np.abs(audio_native)))
    console.print(f"\n[bold]Avant gain :[/bold] RMS={rms_before:.4f}  Peak={peak_before:.4f}")

    # Applique le gain
    audio_boosted = audio_native * GAIN
    # Clip à [-1, 1] pour éviter distorsion
    audio_boosted = np.clip(audio_boosted, -1.0, 1.0)

    rms_after = float(np.sqrt(np.mean(audio_boosted**2)))
    peak_after = float(np.max(np.abs(audio_boosted)))
    console.print(f"[bold]Après gain ×{GAIN:.0f} :[/bold] RMS={rms_after:.4f}  Peak={peak_after:.4f}")

    # Resample vers 16 kHz
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(native_rate, target_rate)
    audio = resample_poly(audio_boosted, target_rate // g, native_rate // g).astype("float32")

    # Sauve un WAV pour debug auditif
    from scipy.io import wavfile
    out_wav = ROOT / "data" / "last_recording_boosted.wav"
    wavfile.write(str(out_wav), target_rate, (audio * 32767).astype(np.int16))
    console.print(f"[dim]WAV boosté sauvé : {out_wav}[/dim]")

    # Whisper
    console.print("\n[yellow]Transcription…[/yellow]")
    text = await stt.transcribe_array(audio)
    console.print(f"\n[bold green]📝 Transcription :[/bold green]")
    console.print(f'[bold]"{text}"[/bold]\n')

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
