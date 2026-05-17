"""FastAPI Jarvis — point d'entrée HTTP.

Routes exposées :
    POST /intent/text        : texte transcrit en entrée, réponse texte + actions
    POST /intent/audio       : audio en entrée, Whisper STT + pipeline complet
    POST /intent/audio_full  : audio en entrée + audio TTS en sortie (binaire)
    GET  /healthz            : santé du service
    GET  /session/state      : état conversation courante (debug)
    POST /session/reset      : réinitialise la session conversationnelle

Auth : Bearer Token (variable d'env JARVIS_HTTP_TOKEN).
Le webhook n8n forwarde via Cloudflare Tunnel sur ces routes.
"""
from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from jarvis.audit.store import SqliteAuditStore
from jarvis.core.command_router import CommandRouter, CommandRouterResult
from jarvis.domain.types import ExecutionMode
from jarvis.orchestrator.llm_client import LLMOrchestrator, load_dotenv_if_present
from jarvis.orchestrator.registry import build_default_registry
from jarvis.orchestrator.session import ConversationSession
from jarvis.orchestrator.tool_router import ToolRouter


# ----------------------------------------------------------------------
# Lifespan : init / cleanup des composants au démarrage
# ----------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise tous les composants une seule fois au démarrage."""
    load_dotenv_if_present()

    # Audit SQLite
    audit_path = Path(os.getenv("JARVIS_AUDIT_DB", "data/audit.db"))
    audit_secret = os.getenv("JARVIS_AUDIT_HMAC_SECRET", "dev-secret-CHANGE-IN-PROD").encode()
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    registry = build_default_registry()
    llm = LLMOrchestrator(registry)
    tool_router = ToolRouter(registry)
    audit = SqliteAuditStore(audit_path, hmac_secret=audit_secret)
    session = ConversationSession()
    mode = ExecutionMode(os.getenv("EXECUTION_MODE", "mock").lower())

    app.state.command_router = CommandRouter(
        registry=registry,
        llm=llm,
        tool_router=tool_router,
        audit=audit,
        session=session,
        mode=mode,
    )

    # STT chargé paresseusement (Whisper prend du temps à charger)
    app.state.stt = None  # lazy : initialisé au premier /intent/audio
    app.state.tts = None  # lazy : initialisé au premier /intent/audio_full

    yield


app = FastAPI(
    title="Jarvis Core",
    description="Backend Python — majordome IA domotique (orchestrateur LLM + sous-agents)",
    version="0.2.0",
    lifespan=lifespan,
)


# ----------------------------------------------------------------------
# Auth Bearer Token
# ----------------------------------------------------------------------

def require_bearer_token(authorization: str | None = Header(default=None)) -> None:
    """Auth simple par Bearer Token (vient du webhook n8n)."""
    expected = os.getenv("JARVIS_HTTP_TOKEN", "")
    if not expected:
        # Pas de token configuré -> mode dev local, on laisse passer
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token requis")
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Token invalide")


# ----------------------------------------------------------------------
# Schémas API
# ----------------------------------------------------------------------

class TextIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="denis", max_length=64)


class ExecutionRecordSchema(BaseModel):
    domain: str
    tool_name: str
    correlation_id: str
    status: str
    duration_ms: int
    error: str | None = None
    response: dict[str, Any] = Field(default_factory=dict)


class IntentResponse(BaseModel):
    speak: str
    executions: list[ExecutionRecordSchema] = Field(default_factory=list)
    llm_latency_ms: int = 0
    llm_provider: str = ""
    llm_model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    rejection_reason: str | None = None


def _result_to_response(result: CommandRouterResult) -> IntentResponse:
    return IntentResponse(
        speak=result.speak,
        executions=[
            ExecutionRecordSchema(
                domain=e.domain,
                tool_name=e.tool_name,
                correlation_id=e.correlation_id,
                status=e.status,
                duration_ms=e.duration_ms,
                error=e.error,
                response=e.response,
            )
            for e in result.executions
        ],
        llm_latency_ms=result.llm_latency_ms,
        llm_provider=result.llm_provider,
        llm_model=result.llm_model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        stop_reason=result.stop_reason,
        rejection_reason=result.rejection_reason,
    )


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    router: CommandRouter = app.state.command_router
    return {
        "status": "ok",
        "version": app.version,
        "mode": router._mode.value if router else "uninit",
        "session_turns": len(router._session.history) if router else 0,
        "stt_loaded": app.state.stt is not None,
        "tts_loaded": app.state.tts is not None,
    }


@app.post("/intent/text", response_model=IntentResponse)
async def intent_text(
    body: TextIntentRequest,
    _: None = Depends(require_bearer_token),
) -> IntentResponse:
    """Pipeline complet à partir d'un texte déjà transcrit."""
    router: CommandRouter = app.state.command_router
    result = await router.handle_text(body.text, now=datetime.utcnow())
    return _result_to_response(result)


@app.post("/intent/audio", response_model=IntentResponse)
async def intent_audio(
    audio: UploadFile = File(...),
    user_id: str = Form(default="denis"),
    _: None = Depends(require_bearer_token),
) -> IntentResponse:
    """Audio en entrée -> Whisper STT -> pipeline complet -> texte en sortie."""
    if app.state.stt is None:
        from jarvis.core.stt import WhisperSTT
        model_size = os.getenv("WHISPER_MODEL", "small")
        app.state.stt = WhisperSTT(model_size=model_size, language="fr")

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        transcribed = await app.state.stt.transcribe_file(tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not transcribed:
        raise HTTPException(status_code=400, detail="Transcription vide")

    router: CommandRouter = app.state.command_router
    result = await router.handle_text(transcribed, now=datetime.utcnow())
    response = _result_to_response(result)
    return JSONResponse(
        content={**response.model_dump(), "transcribed_text": transcribed},
    )


@app.post("/intent/audio_full")
async def intent_audio_full(
    audio: UploadFile = File(...),
    user_id: str = Form(default="denis"),
    _: None = Depends(require_bearer_token),
):
    """Audio en entrée -> texte -> pipeline -> audio TTS en sortie (mp3 binaire)."""
    if app.state.stt is None:
        from jarvis.core.stt import WhisperSTT
        model_size = os.getenv("WHISPER_MODEL", "small")
        app.state.stt = WhisperSTT(model_size=model_size, language="fr")

    if app.state.tts is None:
        from jarvis.core.voice import JarvisTTS
        app.state.tts = JarvisTTS()

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        transcribed = await app.state.stt.transcribe_file(tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not transcribed:
        raise HTTPException(status_code=400, detail="Transcription vide")

    router: CommandRouter = app.state.command_router
    result = await router.handle_text(transcribed, now=datetime.utcnow())

    # Synthèse TTS de la réponse
    tts_out = Path(tempfile.mkdtemp()) / "jarvis_response.mp3"
    await app.state.tts.synthesize(result.speak, tts_out)

    return FileResponse(
        tts_out,
        media_type="audio/mpeg",
        headers={
            "X-Jarvis-Transcribed": transcribed[:500],
            "X-Jarvis-Spoken": result.speak[:500],
            "X-Jarvis-LLM-Latency-Ms": str(result.llm_latency_ms),
            "X-Jarvis-LLM-Provider": result.llm_provider,
            "X-Jarvis-LLM-Model": result.llm_model,
            "X-Jarvis-Tool-Calls": str(len(result.executions)),
        },
    )


@app.get("/session/state")
async def session_state(_: None = Depends(require_bearer_token)) -> dict[str, Any]:
    router: CommandRouter = app.state.command_router
    return {
        "user_id": router._session.user_id,
        "history": router._session.history,
        "last_turn_ts": router._session.last_turn_ts,
    }


@app.post("/session/reset")
async def session_reset(_: None = Depends(require_bearer_token)) -> dict[str, Any]:
    router: CommandRouter = app.state.command_router
    router._session.reset()
    return {"status": "reset", "history_size": 0}
