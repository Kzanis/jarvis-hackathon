"""
STT (Speech-To-Text) — Whisper local.

Capture le micro pendant N secondes, transcrit en texte.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import numpy as np


class WhisperSTT:
    """Wrapper Whisper local. Modèle chargé une fois, réutilisable."""

    def __init__(self, model_size: str = "small", language: str = "fr"):
        import whisper  # import paresseux (whisper est lent à charger)
        self.model = whisper.load_model(model_size)
        self.language = language

    async def transcribe_file(self, audio_path: Path) -> str:
        """Transcrit un fichier audio (wav/mp3) en texte."""
        def _run() -> str:
            result = self.model.transcribe(str(audio_path), language=self.language, fp16=False)
            return result.get("text", "").strip()
        return await asyncio.to_thread(_run)

    async def transcribe_array(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcrit un tableau numpy float32 mono (Whisper attend 16 kHz)."""
        def _run() -> str:
            result = self.model.transcribe(audio.astype(np.float32), language=self.language, fp16=False)
            return result.get("text", "").strip()
        return await asyncio.to_thread(_run)


def record_microphone(duration_seconds: float = 5.0, sample_rate: int = 16000) -> np.ndarray:
    """Enregistre le micro pendant N secondes. Retourne un array mono float32 16 kHz."""
    import sounddevice as sd
    audio = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return audio.flatten()
