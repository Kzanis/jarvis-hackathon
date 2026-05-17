"""
test_whisper_v2.py — Whisper avec cues vocaux Jarvis + device G535 forcé.

Flow :
  1. Jarvis dit "À vous Monsieur" via Edge-TTS (Denis l'entend)
  2. 7 secondes d'enregistrement sur le casque G535 WASAPI explicitement
  3. Jarvis dit "Merci Monsieur"
  4. Whisper transcrit
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

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from rich.console import Console

from jarvis.core.stt import WhisperSTT
from jarvis.core.voice import JarvisTTS

load_dotenv(ROOT / ".env")
console = Console(legacy_windows=False)


def find_g535_device() -> int | None:
    """Cherche le device WASAPI du casque G535."""
    devices = sd.query_devices()
    # Priorité : WASAPI > DirectSound > MME
    candidates_wasapi: list[int] = []
    candidates_other: list[int] = []
    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) == 0:
            continue
        name = dev["name"].lower()
        if "g535" in name or "logitech g535" in name or "casque" in name and "logit" in name:
            host = sd.query_hostapis()[dev["hostapi"]]["name"]
            if "WASAPI" in host:
                candidates_wasapi.append(idx)
            else:
                candidates_other.append(idx)
    if candidates_wasapi:
        return candidates_wasapi[0]
    if candidates_other:
        return candidates_other[0]
    return None


async def main() -> int:
    # 1. TTS pour les cues
    tts = JarvisTTS()
    console.print(f"[dim]TTS backend : {tts.name}[/dim]")

    # 2. STT
    console.print("[yellow]Chargement Whisper…[/yellow]")
    stt = WhisperSTT(model_size="small", language="fr")
    console.print("[green]✓ Whisper prêt[/green]\n")

    # 3. Cherche le casque G535
    g535_idx = find_g535_device()
    if g535_idx is not None:
        dev_info = sd.query_devices(g535_idx)
        host = sd.query_hostapis()[dev_info["hostapi"]]["name"]
        console.print(f"[green]✓ Casque G535 trouvé : #{g535_idx} ({host})[/green]")
    else:
        console.print(f"[yellow]⚠ G535 non trouvé, utilisation du device par défaut[/yellow]")
        g535_idx = None

    # 4. Cue audio : Jarvis dit "À vous Monsieur"
    cue_start_path = ROOT / "data" / "cue_start.mp3"
    if not cue_start_path.exists():
        console.print("[dim]Génération du cue de démarrage…[/dim]")
        await tts.synthesize("À vous Monsieur.", cue_start_path)

    cue_end_path = ROOT / "data" / "cue_end.mp3"
    if not cue_end_path.exists():
        console.print("[dim]Génération du cue de fin…[/dim]")
        await tts.synthesize("Merci Monsieur.", cue_end_path)

    # 5. Joue le cue de démarrage
    console.print("\n[bold cyan]🔊 Jarvis annonce le début…[/bold cyan]")
    os.startfile(str(cue_start_path))  # type: ignore[attr-defined]
    await asyncio.sleep(2.5)  # laisse le temps de jouer le mp3

    # 6. Enregistrement 7 secondes — utilise le sample rate natif du device
    duration = 7.0
    if g535_idx is not None:
        native_rate = int(sd.query_devices(g535_idx)["default_samplerate"])
    else:
        native_rate = 48000
    target_rate = 16000  # Whisper attend 16 kHz
    console.print(f"[dim]Enregistrement à {native_rate} Hz (natif device)[/dim]")
    console.print(f"[bold red]🎙️  ENREGISTREMENT — parle pendant {int(duration)} secondes[/bold red]")
    console.print("[dim]Suggestion : \"Jarvis, ferme le volet de la buanderie\"[/dim]\n")

    audio_native = sd.rec(
        int(duration * native_rate),
        samplerate=native_rate,
        channels=1,
        dtype="float32",
        device=g535_idx,
    )
    sd.wait()
    audio_native = audio_native.flatten()

    # Resample vers 16 kHz pour Whisper (simple decimation linéaire)
    if native_rate != target_rate:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(native_rate, target_rate)
        audio = resample_poly(audio_native, target_rate // g, native_rate // g).astype("float32")
    else:
        audio = audio_native

    # 7. Cue de fin
    os.startfile(str(cue_end_path))  # type: ignore[attr-defined]

    # 8. Analyse du niveau
    rms_max = float(np.sqrt(np.mean(audio**2)))
    peak = float(np.max(np.abs(audio)))
    console.print(f"\n[bold]Niveau audio :[/bold] RMS={rms_max:.4f}  Peak={peak:.4f}")
    if rms_max < 0.001:
        console.print("[red]⚠ Niveau très faible — probablement micro muté ou mauvais device[/red]")

    # 9. Transcription
    console.print("\n[yellow]Transcription Whisper…[/yellow]")
    text = await stt.transcribe_array(audio)
    console.print(f"\n[bold green]📝 Transcription :[/bold green]")
    console.print(f'[bold]"{text}"[/bold]\n')

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
