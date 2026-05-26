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

    def _failure(self, command: DeviceCommand, error: str) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.failure,
            correlation_id=command.correlation_id,
            device_url=_PLAYER_URL,
            action=command.action,
            error=error,
        )


def _clamp_steps(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(_MAX_STEPS, n))
