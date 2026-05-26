"""Sous-agent Freebox Player : pilotage complet de la TV.

Parle DIRECTEMENT au Player Free via l'API « télécommande réseau » :

    http://<player>/pub/remote_control?code=XXXXXXXX&key=<touche>

API exposée par les Player « Free OS » (Révolution, Delta, One, Mini). Un code
à 8 chiffres (réglages du Player) suffit — pas de session HMAC ni token.

Couvre : chaînes (par nom OU numéro), volume, marche/arrêt, navigation (flèches,
OK, retour, accueil), lecture/pause, guide TV. Toutes les actions sont SAFE.

Numérotation des chaînes : la table `_CHANNEL_NUMBERS` reflète la numérotation
RÉELLE de la Freebox de Denis (récupérée via l'API TV, bouquet « Freebox TV »).
La numérotation TNT a changé en 2025 — ne PAS se fier aux anciens numéros.

En mode non-production OU code absent → exécution SIMULÉE (aucun appel réseau).
"""
from __future__ import annotations

import asyncio
import os
import time
import unicodedata
import uuid
from typing import Any

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    ExecutionStatus,
    SensitivityLevel,
)
from jarvis.subagents.base import ToolInvocation, ToolSpec


DOMAIN = "freebox"
_PLAYER_URL = "__freebox_player__"

_DEFAULT_HOST = "hd1.freebox.fr"  # surchargé par FREEBOX_PLAYER_HOST (IP du Player)
_TIMEOUT_S = 5.0
_KEY_DELAY_S = 0.3   # délai entre deux touches d'une même commande
_MAX_STEPS = 20      # garde-fou : pas plus de 20 appuis répétés par commande


def _normalize(value: str) -> str:
    """Minuscule, sans accents/espaces/tirets — pour matcher les noms de chaîne."""
    nfkd = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_only.replace(" ", "").replace("-", "").replace("_", "").replace(".", "").lower()


# Numéro de chaîne RÉEL sur la Freebox de Denis (bouquet « Freebox TV »).
# Clés normalisées via _normalize(). Plusieurs alias possibles par chaîne.
_CHANNEL_NUMBERS: dict[str, int] = {
    "tf1": 1,
    "france2": 2, "fr2": 2,
    "france3": 3, "fr3": 3,
    "france4": 4, "fr4": 4,
    "france5": 5, "fr5": 5,
    "m6": 6,
    "arte": 7,
    "lcp": 8, "lachaineparlementaire": 8, "publicsenat": 8,
    "w9": 9,
    "tmc": 10,
    "tfx": 11,
    "gulli": 12,
    "bfm": 13, "bfmtv": 13,
    "cnews": 14,
    "lci": 15,
    "franceinfo": 16, "info": 16, "franceinfotv": 16,
    "cstar": 17,
    "t18": 18,
    "novo19": 19, "novo": 19,
    "tf1seriesfilms": 20, "tf1series": 20, "seriesfilms": 20,
    "lequipe": 21, "equipe": 21,
    "6ter": 22,
    "rmcstory": 23,
    "rmcdecouverte": 24,
    "rmclife": 25,
    "parispremiere": 28,
    "rtl9": 29,
    "eurosport": 33, "eurosport1": 33,
    "bein": 34, "beinsports": 34, "beinsports1": 34, "bein1": 34,
    "beinsports2": 35, "bein2": 35,
    "beinsports3": 36, "bein3": 36,
    "ligue1": 37, "ligue1plus": 37, "ligue1+": 37,
    "canal": 40, "canalplus": 40, "canal+": 40, "canalp": 40,
}


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="set_channel",
        description=(
            "Met la télé sur une chaîne précise, par son NOM ou son NUMÉRO. "
            "Ex : 'mets CNews' -> channel='CNews' ; 'mets la 6' -> channel='6' ; "
            "'mets TF1' -> channel='TF1'. Revient automatiquement à la télé en direct "
            "avant de changer (utile si on était sur YouTube ou une appli). "
            "Passe le nom tel que dit par l'utilisateur, ne devine PAS le numéro."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["channel"],
            "properties": {
                "channel": {"type": "string", "minLength": 1, "maxLength": 40},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="channel_up",
        description="Chaîne suivante. 'steps' pour monter de plusieurs chaînes (défaut 1).",
        params_schema={
            "type": "object", "additionalProperties": False,
            "properties": {"steps": {"type": "integer", "minimum": 1, "maximum": 20}},
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="channel_down",
        description="Chaîne précédente. 'steps' pour descendre de plusieurs chaînes (défaut 1).",
        params_schema={
            "type": "object", "additionalProperties": False,
            "properties": {"steps": {"type": "integer", "minimum": 1, "maximum": 20}},
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="volume_up",
        description="Monte le volume de la télé. 'steps' = nombre de crans (défaut 3).",
        params_schema={
            "type": "object", "additionalProperties": False,
            "properties": {"steps": {"type": "integer", "minimum": 1, "maximum": 20}},
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="volume_down",
        description="Baisse le volume de la télé. 'steps' = nombre de crans (défaut 3).",
        params_schema={
            "type": "object", "additionalProperties": False,
            "properties": {"steps": {"type": "integer", "minimum": 1, "maximum": 20}},
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="mute",
        description="Coupe (ou rétablit) le son de la télé.",
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="power",
        description="Allume ou éteint la télé (Freebox Player). Bascule l'état actuel.",
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="go_to_tv",
        description=(
            "Revient à la télévision en direct (quitte YouTube, une appli, le menu, "
            "le guide...). À utiliser quand l'utilisateur dit 'reviens à la télé', "
            "'quitte YouTube', 'retour direct'."
        ),
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="navigate",
        description=(
            "Déplace le curseur dans les menus de la Freebox (flèches de la télécommande). "
            "'steps' = nombre d'appuis (défaut 1)."
        ),
        params_schema={
            "type": "object", "additionalProperties": False,
            "required": ["direction"],
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "steps": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="confirm",
        description="Valide (touche OK de la télécommande) — sélectionne l'élément en surbrillance.",
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="back",
        description="Retour en arrière dans les menus (touche retour).",
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="home",
        description="Ouvre l'écran d'accueil de la Freebox (menu principal).",
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="open_guide",
        description="Ouvre le guide des programmes TV.",
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="play_youtube",
        description=(
            "Joue une vidéo YouTube sur la télé à partir d'une demande en langage "
            "naturel. Ex : 'mets la dernière vidéo de Yassine Sdiri' -> "
            "query='Yassine Sdiri' ; 'lance la vidéo X de la chaîne Y' -> query='X Y'. "
            "Trouve la vidéo correspondante, ouvre YouTube sur la télé et la lance "
            "(cast). Par défaut = dernière vidéo du créateur cité."
        ),
        params_schema={
            "type": "object", "additionalProperties": False,
            "required": ["query"],
            "properties": {"query": {"type": "string", "minLength": 2, "maxLength": 120}},
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="tv_program",
        description=(
            "Donne le programme télé du soir (ce qui passe en prime-time, vers 21h) "
            "sur les grandes chaînes, lu depuis le guide de la Freebox. À utiliser pour "
            "'quel est le programme ce soir ?', 'qu'est-ce qu'il y a à la télé ce soir ?'."
        ),
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="open_app",
        description=(
            "Lance une application sur la télé. Pour l'instant : Netflix et YouTube "
            "(touches dédiées). Ex : 'mets Netflix' -> app='netflix', "
            "'lance YouTube' -> app='youtube'."
        ),
        params_schema={
            "type": "object", "additionalProperties": False,
            "required": ["app"],
            "properties": {"app": {"type": "string", "minLength": 2, "maxLength": 32}},
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
    ToolSpec(
        name="playback",
        description=(
            "Contrôle la lecture (direct en pause, replay, vidéo) : lecture, pause, stop, "
            "avance rapide, retour rapide, élément suivant/précédent."
        ),
        params_schema={
            "type": "object", "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "pause", "stop", "forward", "rewind", "next", "previous"],
                },
            },
        },
        default_sensitivity=SensitivityLevel.safe, domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}

# Applis lançables par touche dédiée du Player (validées HTTP 200).
# Les autres (Prime, Disney+, Molotov...) nécessiteront l'API Player Freebox OS
# `control/open` (auth app_token) — non encore implémentée.
_APP_KEYS: dict[str, str] = {
    "netflix": "netflix",
    "youtube": "youtube", "youtub": "youtube", "ytb": "youtube",
}

# Mapping action playback -> touche télécommande
_PLAYBACK_KEYS: dict[str, str] = {
    "play": "play", "pause": "pause", "stop": "stop",
    "forward": "fwd", "rewind": "bwd", "next": "next", "previous": "prev",
}


class FreeboxAgent:
    """Sous-agent Freebox Player. Implémente le Protocol SubAgent."""

    domain: str = DOMAIN
    tools: list[ToolSpec] = TOOLS

    def __init__(self, host: str | None = None, code: str | None = None) -> None:
        self._host = host or os.getenv("FREEBOX_PLAYER_HOST") or _DEFAULT_HOST
        self._code = code if code is not None else os.getenv("FREEBOX_REMOTE_CODE", "")
        self._mode = os.getenv("EXECUTION_MODE", "mock").lower()

    # ----------------- resolve : ToolInvocation -> DeviceCommand -----------------

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand:
        if invocation.domain != DOMAIN:
            raise ValueError(f"FreeboxAgent reçoit un mauvais domaine : {invocation.domain!r}")

        spec = _TOOL_BY_NAME.get(invocation.tool_name)
        if spec is None:
            raise ValueError(
                f"Tool inconnu pour {DOMAIN} : {invocation.tool_name!r}. "
                f"Disponibles : {sorted(_TOOL_BY_NAME)}"
            )

        args: dict[str, Any] = invocation.arguments or {}
        cid = args.get("__correlation_id") or str(uuid.uuid4())
        name = invocation.tool_name

        if name == "play_youtube":
            query = str(args["query"]).strip()
            return DeviceCommand(
                device_url=_PLAYER_URL,
                action=CommandAction.on,
                params={"intent": "play_youtube", "query": query, "keys": []},
                correlation_id=cid,
            )

        if name == "tv_program":
            return DeviceCommand(
                device_url=_PLAYER_URL,
                action=CommandAction.speak,
                params={"intent": "tv_program", "keys": []},
                correlation_id=cid,
            )

        if name == "set_channel":
            number = self._resolve_channel(str(args["channel"]))
            # On revient d'abord à la télé en direct (touche tv), puis on compose le numéro.
            keys = ["tv"] + list(str(number))
            return self._cmd(CommandAction.set_channel, name, keys, cid, {"number": number})

        if name == "channel_up":
            return self._cmd(CommandAction.set_channel, name,
                             ["prgm_inc"] * _clamp_steps(args.get("steps", 1)), cid)

        if name == "channel_down":
            return self._cmd(CommandAction.set_channel, name,
                             ["prgm_dec"] * _clamp_steps(args.get("steps", 1)), cid)

        if name == "volume_up":
            return self._cmd(CommandAction.set_volume, name,
                             ["vol_inc"] * _clamp_steps(args.get("steps", 3)), cid)

        if name == "volume_down":
            return self._cmd(CommandAction.set_volume, name,
                             ["vol_dec"] * _clamp_steps(args.get("steps", 3)), cid)

        if name == "mute":
            return self._cmd(CommandAction.set_volume, name, ["mute"], cid)

        if name == "power":
            return self._cmd(CommandAction.on, name, ["power"], cid)

        if name == "go_to_tv":
            return self._cmd(CommandAction.on, name, ["tv"], cid)

        if name == "navigate":
            return self._cmd(CommandAction.on, name,
                             [args["direction"]] * _clamp_steps(args.get("steps", 1)), cid)

        if name == "confirm":
            return self._cmd(CommandAction.on, name, ["ok"], cid)

        if name == "back":
            return self._cmd(CommandAction.on, name, ["back"], cid)

        if name == "home":
            return self._cmd(CommandAction.on, name, ["home"], cid)

        if name == "open_guide":
            return self._cmd(CommandAction.on, name, ["list"], cid)

        if name == "open_app":
            app_key = _normalize(str(args["app"]))
            key = _APP_KEYS.get(app_key)
            if key is None:
                raise ValueError(
                    f"Appli non disponible : {args['app']!r}. "
                    f"Pour l'instant je sais lancer : Netflix, YouTube."
                )
            return self._cmd(CommandAction.on, name, [key], cid, {"app": key})

        if name == "playback":
            key = _PLAYBACK_KEYS[args["action"]]
            return self._cmd(CommandAction.on, name, [key], cid, {"action": args["action"]})

        raise ValueError(f"Tool reconnu mais non câblé dans resolve() : {name!r}")

    @staticmethod
    def _resolve_channel(value: str) -> int:
        """Nom de chaîne (CNews, TF1...) OU numéro -> numéro entier de chaîne."""
        s = value.strip()
        key = _normalize(s)
        if key in _CHANNEL_NUMBERS:
            return _CHANNEL_NUMBERS[key]
        # Numéro composé directement, éventuellement avec un mot de liaison
        # ("la 6", "chaîne 33", "mets 12") -> on retire les mots et on lit le nombre.
        stripped = key
        for filler in ("chaine", "numero", "mets", "met", "sur", "la", "le"):
            stripped = stripped.replace(filler, "")
        if stripped.isdigit():
            return int(stripped)
        raise ValueError(
            f"Chaîne inconnue : {value!r}. Donne un numéro, ou un nom connu "
            f"(ex: TF1, CNews, M6, BFM TV...)."
        )

    @staticmethod
    def _cmd(action: CommandAction, intent: str, keys: list[str], cid: str,
             extra: dict[str, Any] | None = None) -> DeviceCommand:
        params: dict[str, Any] = {"intent": intent, "keys": keys}
        if extra:
            params.update(extra)
        return DeviceCommand(device_url=_PLAYER_URL, action=action, params=params, correlation_id=cid)

    # ----------------- execute : DeviceCommand -> ExecutionResult -----------------

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        if command.params.get("intent") == "play_youtube":
            return await self._exec_play_youtube(command)

        if command.params.get("intent") == "tv_program":
            return await self._exec_tv_program(command)

        keys: list[str] = command.params.get("keys", [])
        if not keys:
            return self._failure(command, "Aucune touche à envoyer.")

        if self._mode != "production" or not self._code:
            return ExecutionResult(
                status=ExecutionStatus.success,
                correlation_id=command.correlation_id,
                device_url=_PLAYER_URL,
                action=command.action,
                duration_ms=0,
                response={"simulated": True, "intent": command.params.get("intent"), "keys": keys},
            )

        try:
            duration_ms = await asyncio.to_thread(self._send_keys_sync, keys)
        except Exception as e:  # noqa: BLE001
            return self._failure(command, f"Télécommande Freebox injoignable : {type(e).__name__}: {e}")

        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=_PLAYER_URL,
            action=command.action,
            duration_ms=duration_ms,
            response={"intent": command.params.get("intent"), "keys": keys},
        )

    def _send_keys_sync(self, keys: list[str]) -> int:
        import requests

        url = f"http://{self._host}/pub/remote_control"
        start = time.monotonic()
        for i, key in enumerate(keys):
            if i:
                time.sleep(_KEY_DELAY_S)
            resp = requests.get(url, params={"code": self._code, "key": key}, timeout=_TIMEOUT_S)
            resp.raise_for_status()
        return int((time.monotonic() - start) * 1000)

    # ----------------- play_youtube : recherche + cast -----------------

    async def _exec_play_youtube(self, command: DeviceCommand) -> ExecutionResult:
        query = str(command.params.get("query", "")).strip()
        if not query:
            return self._failure(command, "Aucun créateur / vidéo demandé.")

        if self._mode != "production" or not self._code:
            return ExecutionResult(
                status=ExecutionStatus.success,
                correlation_id=command.correlation_id,
                device_url=_PLAYER_URL, action=command.action, duration_ms=0,
                response={"simulated": True, "intent": "play_youtube", "query": query},
            )
        try:
            video_id, title = await asyncio.to_thread(_find_latest_video, query)
        except Exception as e:  # noqa: BLE001
            return self._failure(command, f"Vidéo introuvable pour {query!r} : {type(e).__name__}: {e}")
        try:
            # Ouvre l'appli YouTube sur la télé (le cast échoue si elle n'est pas au premier plan),
            # laisse-lui le temps de démarrer, puis pousse la vidéo.
            await asyncio.to_thread(self._send_keys_sync, ["youtube"])
            await asyncio.sleep(_YT_OPEN_DELAY_S)
            await _cast_video(video_id)
        except Exception as e:  # noqa: BLE001
            return self._failure(command, f"Cast YouTube impossible : {type(e).__name__}: {e}")
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=_PLAYER_URL, action=command.action,
            response={"intent": "play_youtube", "query": query, "video_id": video_id, "title": title},
        )

    # ----------------- tv_program : programme du soir via guide Freebox -----------------

    async def _exec_tv_program(self, command: DeviceCommand) -> ExecutionResult:
        if self._mode != "production":
            answer = ("Ce soir : sur TF1, un divertissement ; sur France 2, un film ; "
                      "sur M6, une série. (simulation)")
            return ExecutionResult(
                status=ExecutionStatus.success, correlation_id=command.correlation_id,
                device_url=_PLAYER_URL, action=command.action, duration_ms=0,
                response={"simulated": True, "intent": "tv_program", "answer": answer},
            )
        try:
            answer = await asyncio.to_thread(_fetch_tv_tonight)
        except Exception as e:  # noqa: BLE001
            return self._failure(command, f"Guide TV indisponible : {type(e).__name__}: {e}")
        return ExecutionResult(
            status=ExecutionStatus.success, correlation_id=command.correlation_id,
            device_url=_PLAYER_URL, action=command.action,
            response={"intent": "tv_program", "answer": answer},
        )

    def _failure(self, command: DeviceCommand, error: str) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.failure,
            correlation_id=command.correlation_id,
            device_url=_PLAYER_URL,
            action=command.action,
            error=error,
        )


_YT_OPEN_DELAY_S = 6.0  # délai après ouverture de l'appli YouTube avant le cast
_YT_AUTH_FILE = os.getenv("FREEBOX_YT_AUTH_FILE", "jarvis_yt_auth.json")

# Serveur Freebox (le routeur) pour l'API TV/EPG — distinct du Player.
_SERVER_HOST = os.getenv("FREEBOX_SERVER_HOST", "192.168.1.254")
_TV_BOUQUET_ID = os.getenv("FREEBOX_TV_BOUQUET_ID", "772")  # bouquet "Freebox TV"
# Grandes chaînes pour le programme du soir (numéro -> ordre de lecture).
_TONIGHT_CHANNELS = [1, 2, 3, 5, 6, 7, 9, 10]
_PRIME_TIME = (21, 10)  # heure locale du prime-time visé


def _fetch_tv_tonight() -> str:
    """Lit le guide Freebox et renvoie une phrase orale du programme de ce soir."""
    import json
    import time
    import urllib.request
    from datetime import datetime

    def _get(path: str):
        url = f"http://{_SERVER_HOST}/api/v8/tv/{path}"
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)["result"]

    chans = _get("channels")
    bouquet = _get(f"bouquets/{_TV_BOUQUET_ID}/channels")
    num_to_uuid: dict[int, str] = {}
    for it in bouquet:
        n, u = it.get("number"), it.get("uuid")
        if n is not None and u and n not in num_to_uuid:
            num_to_uuid[n] = u

    now = datetime.now()
    soir = now.replace(hour=_PRIME_TIME[0], minute=_PRIME_TIME[1], second=0, microsecond=0)
    t = int(time.mktime(soir.timetuple()))
    epg = _get(f"epg/by_time/{t}")

    parts: list[str] = []
    for n in _TONIGHT_CHANNELS:
        u = num_to_uuid.get(n)
        if not u:
            continue
        name = (chans.get(u, {}) or {}).get("name", "")
        title = None
        for p in (epg.get(u, {}) or {}).values():
            d, dur = p.get("date", 0), p.get("duration", 0)
            if d <= t < d + dur:
                title = p.get("title")
                break
        if name and title:
            parts.append(f"sur {name}, {title}")

    if not parts:
        return "Je ne parviens pas à lire le programme de ce soir, Monsieur."
    return "Ce soir à la télévision : " + " ; ".join(parts) + "."


def _find_latest_video(query: str) -> tuple[str, str]:
    """Trouve la dernière vidéo d'un créateur/recherche. Retourne (video_id, titre).

    Sans clé API : via yt-dlp. On localise d'abord la chaîne (recherche), puis on
    prend la 1re vidéo de son onglet /videos (trié du plus récent au plus ancien).
    """
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "no_warnings": True, "extract_flat": True,
            "skip_download": True, "playlist_items": "1"}
    with YoutubeDL(opts) as ydl:
        res = ydl.extract_info(f"ytsearch1:{query}", download=False)
        entries = (res or {}).get("entries") or []
        if not entries:
            raise RuntimeError("aucun résultat YouTube")
        first = entries[0]
        channel_url = first.get("channel_url") or first.get("uploader_url")
        if channel_url:
            info = ydl.extract_info(channel_url.rstrip("/") + "/videos", download=False)
            vids = (info or {}).get("entries") or []
            if vids:
                v = vids[0]
                return v["id"], v.get("title", "")
        # Repli : la vidéo trouvée par la recherche directe
        return first["id"], first.get("title", "")


async def _cast_video(video_id: str) -> None:
    """Pousse une vidéo sur l'écran YouTube apparié (YouTube Lounge API)."""
    import json

    from pyytlounge import YtLoungeApi

    with open(_YT_AUTH_FILE, encoding="utf-8") as fh:
        auth = json.load(fh)
    async with YtLoungeApi("Jarvis") as api:
        api.load_auth_state(auth)
        if not await api.refresh_auth():
            raise RuntimeError("liaison YouTube expirée (ré-appairage nécessaire)")
        if not await api.connect():
            raise RuntimeError("écran YouTube injoignable (appli fermée ?)")
        if not await api.play_video(video_id):
            raise RuntimeError("la TV a refusé la lecture")


def _clamp_steps(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(_MAX_STEPS, n))
