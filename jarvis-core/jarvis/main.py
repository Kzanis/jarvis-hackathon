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

import asyncio
import base64
import json
import os
import re
import secrets
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from jarvis.audit.store import SqliteAuditStore
from jarvis.core.command_router import CommandRouter, CommandRouterResult
from jarvis.domain.types import ExecutionMode
from jarvis.orchestrator.llm_client import LLMOrchestrator, load_dotenv_if_present
from jarvis.orchestrator.registry import build_default_registry
from jarvis.orchestrator.session import ConversationSession
from jarvis.orchestrator.tool_router import ToolRouter
from jarvis.policy import roles as roles_mod
from jarvis.policy.roles import ADMIN, DEFAULT_TITLE_BY_ROLE, KNOWN_ROLES, RolePolicy


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

    # Politique d'accès par rôle (RBAC, PRD §30). Partagée entre le routeur
    # (contrôle à chaque commande) et les routes /admin (élévation en direct).
    role_policy = RolePolicy()
    app.state.role_policy = role_policy

    app.state.command_router = CommandRouter(
        registry=registry,
        llm=llm,
        tool_router=tool_router,
        audit=audit,
        session=session,
        mode=mode,
        role_policy=role_policy,
    )

    # STT chargé paresseusement (Whisper prend du temps à charger)
    app.state.stt = None  # lazy : initialisé au premier /intent/audio

    # TTS chargé au démarrage (utilisé sur chaque /intent/text pour la voix Andrew)
    try:
        from jarvis.core.voice import JarvisTTS

        app.state.tts = JarvisTTS()
    except Exception as e:
        # Échec init TTS : la PWA basculera sur sa synthèse navigateur fallback
        print(f"[Jarvis] Échec init JarvisTTS : {e}")
        app.state.tts = None

    yield


app = FastAPI(
    title="Jarvis Core",
    description="Backend Python — majordome IA domotique (orchestrateur LLM + sous-agents)",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — la PWA (site statique Hostinger) appelle certaines routes du backend
# EN DIRECT (accueil /auth/welcome, /admin/*), pas via n8n. On autorise donc
# l'origine du front. Bearer token dans l'en-tête Authorization (pas de cookie),
# donc allow_credentials reste False. Origines configurables via JARVIS_CORS_ORIGINS.
_cors_origins = [
    o.strip()
    for o in os.getenv(
        "JARVIS_CORS_ORIGINS",
        "https://jarvis.creatorsystemia.fr,http://localhost:3000",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ----------------------------------------------------------------------
# Auth — Sessions Bearer Token (PRD §9.1)
# ----------------------------------------------------------------------

# Identifiants login PWA (à définir via env vars sur la VM)
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "denis")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "CHANGE_ME_AUTH_PWD")
AUTH_SESSION_TTL_HOURS = int(os.getenv("AUTH_SESSION_TTL_HOURS", "4"))

# Titre d'adresse du compte principal (Denis). Les comptes additionnels portent
# leur propre titre via JARVIS_EXTRA_USERS.
AUTH_TITLE = os.getenv("AUTH_TITLE", "Monsieur")


def _load_users() -> dict[str, dict[str, str]]:
    """Table {username: {"password", "title", "role"}} des comptes autorisés.

    - Compte principal : AUTH_USERNAME / AUTH_PASSWORD (titre AUTH_TITLE, rôle ``admin``).
    - Comptes additionnels : variable JARVIS_EXTRA_USERS, un JSON du type
      [{"username": "jury", "title": "Votre Sagacité", "role": "visiteur"}].
      • "password" omis  -> hérite du mot de passe principal (couple partageant le code).
      • "title" omis     -> titre par défaut du rôle (DEFAULT_TITLE_BY_ROLE).
      • "role" omis      -> ``admin`` (non-régression : les comptes additionnels
        existants, ex. Madame, restent des comptes de confiance). Pour brider un
        compte, préciser explicitement "role": "locataire" ou "visiteur".
    """
    users: dict[str, dict[str, str]] = {}
    if AUTH_PASSWORD != "CHANGE_ME_AUTH_PWD":
        users[AUTH_USERNAME] = {"password": AUTH_PASSWORD, "title": AUTH_TITLE, "role": ADMIN}
    raw = os.getenv("JARVIS_EXTRA_USERS", "").strip()
    if raw:
        try:
            for entry in json.loads(raw):
                u = str(entry.get("username", "")).strip()
                # Mot de passe optionnel : hérite de AUTH_PASSWORD si absent.
                p = str(entry.get("password", "")) or AUTH_PASSWORD
                role = str(entry.get("role", "")).strip().lower()
                if role not in KNOWN_ROLES:
                    role = ADMIN  # défaut non-régression pour comptes de confiance
                t = str(entry.get("title", "")).strip() or DEFAULT_TITLE_BY_ROLE.get(role, "Monsieur")
                if u and p and p != "CHANGE_ME_AUTH_PWD":
                    users[u] = {"password": p, "title": t, "role": role}
        except Exception as e:  # JSON malformé -> on ignore les comptes additionnels
            print(f"[Jarvis] WARN: JARVIS_EXTRA_USERS invalide ({e})")
    return users


def _title_for(user_id: str) -> str:
    """Titre d'adresse ('Monsieur'/'Madame'/'Votre Sagacité') associé à un identifiant."""
    entry = _load_users().get(user_id)
    return entry["title"] if entry else AUTH_TITLE


def _role_for(user_id: str) -> str:
    """Rôle RBAC associé à un identifiant (défaut ``admin`` pour le compte principal)."""
    entry = _load_users().get(user_id)
    return entry.get("role", ADMIN) if entry else ADMIN


def _apply_title(text: str, title: str) -> str:
    """Adapte le titre d'adresse dans la phrase parlée selon l'utilisateur.

    Le corpus majordome emploie 'Monsieur' en apposition (vocatif) : une
    substitution directe respecte donc la syntaxe. No-op pour le titre défaut.
    """
    if not text or title == "Monsieur":
        return text
    return text.replace("Monsieur", title).replace("monsieur", title.lower())


def _clean_display_name(raw: str | None) -> str | None:
    """Valide le nom d'adresse choisi par l'utilisateur (PRD §30.4).

    Retourne un titre propre utilisable comme vocatif, ou None si l'entrée est
    vide/inexploitable (on retombe alors sur le titre du compte). Garde-fou : on
    borne la longueur, on retire les retours ligne et on rejette tout ce qui
    ressemble à une injection (le nom est inséré dans une phrase puis synthétisé).
    """
    if not raw:
        return None
    name = " ".join(raw.split()).strip(" .,:;!?\"'")
    if not (1 < len(name) <= 40):
        return None
    # Lettres (accents inclus), espaces, traits d'union, apostrophes uniquement.
    if not all(c.isalpha() or c in " -'" for c in name):
        return None
    return name


def _strip_markdown(text: str) -> str:
    """Retire le balisage markdown d'une phrase destinée à être PRONONCÉE.

    Sans cela, la synthèse vocale lit « astérisque astérisque » sur un **gras**
    (constat démo 03/06). On enlève *, #, `, > et les puces de liste.
    """
    if not text:
        return text
    t = re.sub(r"[*#`>]", "", text)
    t = re.sub(r"(?m)^\s*[-•]\s+", "", t)  # puces en début de ligne
    return re.sub(r"[ \t]{2,}", " ", t).strip()


# Stockage in-memory des sessions (suffisant pour 1 user en MVP)
# Format : {token: {"user_id": str, "expires_at": datetime}}
_SESSIONS: dict[str, dict[str, Any]] = {}


def _cleanup_expired_sessions(now: datetime) -> None:
    expired = [t for t, s in _SESSIONS.items() if s["expires_at"] < now]
    for t in expired:
        _SESSIONS.pop(t, None)


def require_session(authorization: str | None = Header(default=None)) -> str:
    """Valide le Bearer Token de session (login obligatoire) — retourne user_id."""
    if AUTH_PASSWORD == "CHANGE_ME_AUTH_PWD":
        # Mode dev / placeholder non remplacé : on laisse passer mais on log
        print("[Jarvis] WARN: AUTH_PASSWORD non configuré, auth désactivée")
        return "denis"

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token de session requis")
    token = authorization.split(" ", 1)[1].strip()
    session = _SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalide")
    if session["expires_at"] < datetime.utcnow():
        _SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expirée")
    return session["user_id"]


# Compat ascendante : ancien Depends utilisé par /intent/audio*
def require_bearer_token(authorization: str | None = Header(default=None)) -> None:
    require_session(authorization)


def require_admin(user_id: str = Depends(require_session)) -> str:
    """Exige une session dont le rôle RBAC est ``admin`` (routes d'administration)."""
    if _role_for(user_id) != ADMIN:
        raise HTTPException(status_code=403, detail="Action réservée à l'administrateur")
    return user_id


# ----------------------------------------------------------------------
# Schémas API
# ----------------------------------------------------------------------

class TextIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="denis", max_length=64)
    # Nom d'adresse choisi par l'utilisateur (« comment dois-je vous appeler ? »).
    # Optionnel : s'il est fourni, il prime sur le titre du compte (PRD §30.4).
    display_name: str | None = Field(default=None, max_length=40)


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
# Schémas Auth
# ----------------------------------------------------------------------

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


class LoginResponse(BaseModel):
    token: str
    user_id: str
    title: str = "Monsieur"
    role: str = "admin"
    expires_at: str  # ISO 8601


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.post("/auth/login", response_model=LoginResponse)
async def auth_login(body: LoginRequest) -> LoginResponse:
    """Login PWA — vérifie identifiants contre AUTH_USERNAME/AUTH_PASSWORD env.

    Renvoie un token de session valable AUTH_SESSION_TTL_HOURS heures.
    """
    users = _load_users()
    if not users:
        raise HTTPException(
            status_code=503,
            detail="Auth non configurée — AUTH_PASSWORD doit être défini dans .env serveur",
        )

    # Protection bruteforce minimale (délai constant si KO) + comparaison constante
    entry = users.get(body.username)
    valid = entry is not None and secrets.compare_digest(body.password, entry["password"])
    if not valid:
        await asyncio.sleep(0.5)
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=AUTH_SESSION_TTL_HOURS)
    _SESSIONS[token] = {"user_id": body.username, "expires_at": expires_at}
    _cleanup_expired_sessions(datetime.utcnow())

    return LoginResponse(
        token=token,
        user_id=body.username,
        title=entry["title"],
        role=entry.get("role", ADMIN),
        expires_at=expires_at.isoformat() + "Z",
    )


@app.post("/auth/logout")
async def auth_logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """Invalide le token de session courant."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        _SESSIONS.pop(token, None)
    return {"status": "logged_out"}

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


# Garde-fou de latence : au-delà de ce délai, on abandonne la voix Andrew et on
# laisse le front parler en synthèse navigateur. Réglé à 20s pour PRÉSERVER la voix
# Andrew sur les réponses un peu longues (présentation ~13s observée) tout en
# restant sous le timeout du nœud HTTP n8n « Appel Jarvis Freebox » (45s — PRD §30.12).
TTS_SYNTH_TIMEOUT_S = 20.0


async def _synthesize_speak_audio(text: str) -> str | None:
    """Synthétise la phrase majordome via Edge-TTS Andrew, retourne le mp3 en base64.

    Renvoie None si le service TTS n'est pas disponible, si la synthèse échoue, ou
    si elle dépasse TTS_SYNTH_TIMEOUT_S — la PWA basculera alors sur sa synthèse
    navigateur (Web Speech). Le garde-fou de délai évite que la synthèse d'une
    longue réponse bloque la route au-delà du timeout du webhook n8n (PRD §30.12).
    """
    tts = getattr(app.state, "tts", None)
    text = _strip_markdown(text)  # filet : jamais de « astérisque » prononcé
    if tts is None or not text.strip():
        return None
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_mp3 = tmp_dir / "speak.mp3"
    try:
        await asyncio.wait_for(tts.synthesize(text, tmp_mp3), timeout=TTS_SYNTH_TIMEOUT_S)
        audio_bytes = tmp_mp3.read_bytes()
        return base64.b64encode(audio_bytes).decode("ascii")
    except asyncio.TimeoutError:
        print(f"[Jarvis] TTS synthèse trop lente (>{TTS_SYNTH_TIMEOUT_S}s) — repli voix navigateur")
        return None
    except Exception as e:
        print(f"[Jarvis] TTS synthèse échouée : {e}")
        return None
    finally:
        try:
            tmp_mp3.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except Exception:
            pass


@app.post("/intent/text")
async def intent_text(
    body: TextIntentRequest,
    user_id: str = Depends(require_session),
) -> JSONResponse:
    """Pipeline complet à partir d'un texte déjà transcrit.

    Retourne le JSON IntentResponse enrichi avec `speak_audio_base64` (mp3 Andrew)
    pour que la PWA puisse jouer la vraie voix Jarvis plutôt que la voix système.
    """
    router: CommandRouter = app.state.command_router
    result = await router.handle_text(
        body.text, now=datetime.utcnow(), role=_role_for(user_id)
    )
    # Titre d'adresse : le nom choisi par l'utilisateur prime sur le titre du
    # compte (PRD §30.4). Appliqué au texte ET à la voix Andrew.
    title = _clean_display_name(body.display_name) or _title_for(user_id)
    result.speak = _strip_markdown(_apply_title(result.speak, title))
    response = _result_to_response(result)

    audio_b64 = await _synthesize_speak_audio(result.speak)
    payload = {
        **response.model_dump(),
        "speak_audio_base64": audio_b64,
        "speak_audio_mime": "audio/mpeg" if audio_b64 else None,
    }
    return JSONResponse(content=payload)


@app.post("/intent/audio", response_model=IntentResponse)
async def intent_audio(
    audio: UploadFile = File(...),
    user_id: str = Form(default="denis"),  # conservé pour compat front ; PAS utilisé pour la sécurité
    session_user_id: str = Depends(require_session),
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
    result = await router.handle_text(
        transcribed, now=datetime.utcnow(), role=_role_for(session_user_id)
    )
    result.speak = _apply_title(result.speak, _title_for(session_user_id))
    response = _result_to_response(result)
    return JSONResponse(
        content={**response.model_dump(), "transcribed_text": transcribed},
    )


@app.post("/intent/audio_full")
async def intent_audio_full(
    audio: UploadFile = File(...),
    user_id: str = Form(default="denis"),  # conservé pour compat front ; PAS utilisé pour la sécurité
    session_user_id: str = Depends(require_session),
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
    result = await router.handle_text(
        transcribed, now=datetime.utcnow(), role=_role_for(session_user_id)
    )
    result.speak = _apply_title(result.speak, _title_for(session_user_id))

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
async def session_state(_: str = Depends(require_admin)) -> dict[str, Any]:
    router: CommandRouter = app.state.command_router
    return {
        "user_id": router._session.user_id,
        "history": router._session.history,
        "last_turn_ts": router._session.last_turn_ts,
    }


@app.post("/session/reset")
async def session_reset(_: str = Depends(require_admin)) -> dict[str, Any]:
    router: CommandRouter = app.state.command_router
    router._session.reset()
    return {"status": "reset", "history_size": 0}


# ----------------------------------------------------------------------
# RBAC — accueil selon le rôle + administration (PRD §30)
# ----------------------------------------------------------------------

class RoleCapabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., min_length=1, max_length=32)
    capability: str = Field(..., min_length=1, max_length=32)  # "safe" | "sensible" | "critique"
    allowed: bool


class DisconnectRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(default="visiteur", min_length=1, max_length=32)


@app.get("/auth/welcome")
async def auth_welcome(
    user_id: str = Depends(require_session),
    display_name: str | None = None,
) -> JSONResponse:
    """Discours d'accueil prononcé à la connexion, adapté au rôle (texte + voix Andrew).

    ``display_name`` (query, optionnel) : nom mémorisé par le front aux connexions
    suivantes — personnalise l'accueil (« Bonjour <Nom> ») au lieu du titre par défaut.
    """
    role = _role_for(user_id)
    title = _clean_display_name(display_name) or _title_for(user_id)
    speak = _strip_markdown(_apply_title(roles_mod.welcome_speech(role), title))
    audio_b64 = await _synthesize_speak_audio(speak)
    return JSONResponse(content={
        "speak": speak,
        "role": role,
        "title": title,
        "speak_audio_base64": audio_b64,
        "speak_audio_mime": "audio/mpeg" if audio_b64 else None,
    })


@app.get("/admin/roles")
async def admin_get_roles(_: str = Depends(require_admin)) -> dict[str, Any]:
    """État courant des capacités par rôle (pour l'écran admin)."""
    policy: RolePolicy = app.state.role_policy
    return {
        "roles": policy.snapshot(),
        "capabilities": list(roles_mod.EDITABLE_CAPABILITIES),
    }


@app.post("/admin/roles")
async def admin_set_role(
    body: RoleCapabilityUpdate,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    """Accorde/retire un niveau d'action à un rôle (élévation en direct, PRD §30.5)."""
    policy: RolePolicy = app.state.role_policy
    target = body.role.strip().lower()
    if target == ADMIN:
        raise HTTPException(status_code=400, detail="Le rôle admin ne peut être modifié")
    if target not in KNOWN_ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle inconnu : {body.role}")
    if body.capability not in roles_mod.EDITABLE_CAPABILITIES:
        raise HTTPException(status_code=400, detail=f"Capacité inconnue : {body.capability}")
    policy.set_level(target, body.capability, body.allowed)
    return {"status": "ok", "roles": policy.snapshot()}


@app.post("/admin/disconnect-role")
async def admin_disconnect_role(
    body: DisconnectRoleRequest,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    """Invalide toutes les sessions des utilisateurs portant ce rôle (déconnexion jury, PRD §30.6)."""
    target = body.role.strip().lower()
    if target == ADMIN:
        raise HTTPException(status_code=400, detail="Impossible de déconnecter le rôle administrateur")
    revoked = 0
    for token in list(_SESSIONS.keys()):
        sess = _SESSIONS.get(token)
        if sess and _role_for(sess["user_id"]) == target:
            _SESSIONS.pop(token, None)
            revoked += 1
    return {"status": "disconnected", "role": target, "sessions_closed": revoked}
