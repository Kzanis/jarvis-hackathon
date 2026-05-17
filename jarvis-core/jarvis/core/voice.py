"""
Pipeline vocal Jarvis — abstraction multi-backend.

Backends TTS supportés :
  - "edge"       : Microsoft Edge-TTS (Neural) — GRATUIT, illimité, voix Andrew par défaut
  - "elevenlabs" : ElevenLabs (premium) — payant Creator tier pour voix typées
  - "openai"     : OpenAI tts-1 (fable, onyx...) — quelques cents

Choix du backend via .env : TTS_BACKEND=edge|elevenlabs|openai
"""
from __future__ import annotations

import asyncio
import os
import platform
import subprocess
from pathlib import Path
from typing import Literal, Optional, Protocol

Backend = Literal["edge", "elevenlabs", "openai"]


# ============================================
# Protocol commun
# ============================================

class TTSBackend(Protocol):
    """Tout backend TTS doit implémenter synthesize."""
    async def synthesize(self, text: str, out_path: Path) -> Path: ...


# ============================================
# Backend Edge-TTS (Microsoft Neural — gratuit)
# ============================================

class EdgeTTSBackend:
    """Microsoft Edge-TTS — gratuit, illimité, voix Neural."""

    def __init__(self, voice_id: str = "en-US-AndrewMultilingualNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        import edge_tts  # import paresseux
        self._edge_tts = edge_tts
        self.voice_id = voice_id
        self.rate = rate
        self.pitch = pitch

    async def synthesize(self, text: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = self._edge_tts.Communicate(text, self.voice_id, rate=self.rate, pitch=self.pitch)
        await communicate.save(str(out_path))
        return out_path


# ============================================
# Backend ElevenLabs (premium)
# ============================================

class ElevenLabsBackend:
    """ElevenLabs — voix typées (nécessite Creator tier pour Voice Library)."""

    def __init__(self, api_key: str, voice_id: str = "pNInz6obpgDQGcFmaJgB", model_id: str = "eleven_multilingual_v2"):
        from elevenlabs.client import ElevenLabs
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY requise pour backend elevenlabs")
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.model_id = model_id

    async def synthesize(self, text: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # ElevenLabs SDK est sync → on l'exécute dans un thread pour ne pas bloquer
        def _generate() -> None:
            stream = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format="mp3_44100_128",
            )
            with open(out_path, "wb") as f:
                for chunk in stream:
                    if chunk:
                        f.write(chunk)
        await asyncio.to_thread(_generate)
        return out_path


# ============================================
# Backend OpenAI (fable, onyx, etc.)
# ============================================

class OpenAITTSBackend:
    """OpenAI tts-1 — voix fable (UK narrative), onyx (grave), etc."""

    def __init__(self, api_key: str, voice_id: str = "fable", model: str = "tts-1"):
        import openai
        if not api_key:
            raise ValueError("OPENAI_API_KEY requise pour backend openai")
        self.client = openai.OpenAI(api_key=api_key)
        self.voice_id = voice_id
        self.model = model

    async def synthesize(self, text: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        def _generate() -> None:
            r = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice_id,
                input=text,
            )
            r.stream_to_file(str(out_path))
        await asyncio.to_thread(_generate)
        return out_path


# ============================================
# Façade unifiée — choisit le backend
# ============================================

class JarvisTTS:
    """Façade : choisit le backend selon TTS_BACKEND dans .env."""

    def __init__(
        self,
        backend: Optional[Backend] = None,
        voice_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        # Résolution backend depuis .env si non passé
        b = backend or os.getenv("TTS_BACKEND", "edge").lower()  # type: ignore

        if b == "edge":
            vid = voice_id or os.getenv("TTS_VOICE_ID", "en-US-AndrewMultilingualNeural")
            self._backend: TTSBackend = EdgeTTSBackend(voice_id=vid)
            self.name = f"edge:{vid}"
        elif b == "elevenlabs":
            key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
            vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
            self._backend = ElevenLabsBackend(api_key=key, voice_id=vid)
            self.name = f"elevenlabs:{vid[:8]}"
        elif b == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY", "")
            vid = voice_id or os.getenv("OPENAI_TTS_VOICE", "fable")
            self._backend = OpenAITTSBackend(api_key=key, voice_id=vid)
            self.name = f"openai:{vid}"
        else:
            raise ValueError(f"Backend TTS inconnu : {b!r} (attendu edge|elevenlabs|openai)")

    async def synthesize(self, text: str, out_path: Path) -> Path:
        return await self._backend.synthesize(text, out_path)

    async def speak(self, text: str, out_path: Optional[Path] = None) -> Path:
        """Synthétise et joue le fichier (Windows : start, Mac : open, Linux : xdg-open)."""
        if out_path is None:
            out_path = Path("data") / "tts_last.mp3"
        path = await self.synthesize(text, out_path)
        system = platform.system()
        if system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return path
