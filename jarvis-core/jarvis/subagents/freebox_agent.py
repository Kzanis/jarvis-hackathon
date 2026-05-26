"""Sous-agent Freebox Player : pilotage de la TV (chaînes, volume, marche/arrêt).

Contrairement à TaHoma (qui passe par un handler Overkiz) ou Devialet (mock),
ce sous-agent parle DIRECTEMENT au Player Free via l'API « télécommande réseau » :

    http://<player>/pub/remote_control?code=XXXXXXXX&key=<touche>

Cette API est exposée par les Player « Free OS » (Révolution, Delta, One, Mini).
Un code à 8 chiffres, activé dans les réglages du Player, suffit — aucune session
HMAC ni token applicatif n'est nécessaire pour zapper / régler le volume.

Touches utilisées (clavier de la télécommande Free) :
    prgm_inc / prgm_dec  -> chaîne suivante / précédente
    vol_inc  / vol_dec   -> volume + / -
    mute                 -> coupe / rétablit le son
    power                -> allume / éteint le Player
    0..9                 -> composer un numéro de chaîne

Toutes les actions sont SAFE (réversibles, faible conséquence — cf. PRD §9).
En mode non-production (jury/dev), l'exécution est SIMULÉE : aucun appel réseau.
"""
from __future__ import annotations

import asyncio
import os
import time
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

# Hôte du Player. Sur le réseau local, "hd1.freebox.fr" résout vers le Player
# Free OS. Surchageable via .env si le Player a une IP fixe dédiée.
_DEFAULT_HOST = "hd1.freebox.fr"
_TIMEOUT_S = 5.0
# Délai entre deux touches d'une même commande (composition d'un numéro de chaîne,
# répétition volume/chaîne) — laisse le Player encaisser chaque appui.
_KEY_DELAY_S = 0.25
_MAX_STEPS = 20  # garde-fou : pas plus de 20 appuis répétés par commande


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="channel_up",
        description=(
            "Passe à la chaîne suivante sur la télé (Freebox). "
            "'steps' permet de monter de plusieurs chaînes d'un coup (défaut 1)."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "steps": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="channel_down",
        description=(
            "Passe à la chaîne précédente sur la télé (Freebox). "
            "'steps' pour descendre de plusieurs chaînes d'un coup (défaut 1)."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "steps": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="set_channel",
        description=(
            "Va directement à une chaîne par son NUMÉRO sur la télé (Freebox). "
            "Ex : 'mets la 6' -> number=6, 'mets TF1' -> number=1. "
            "Compose le numéro touche par touche."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["number"],
            "properties": {
                "number": {"type": "integer", "minimum": 1, "maximum": 999},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="volume_up",
        description="Monte le volume de la télé (Freebox). 'steps' = nombre de crans (défaut 3).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "steps": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="volume_down",
        description="Baisse le volume de la télé (Freebox). 'steps' = nombre de crans (défaut 3).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "steps": {"type": "integer", "minimum": 1, "maximum": 20},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="mute",
        description="Coupe (ou rétablit) le son de la télé (Freebox).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="power",
        description="Allume ou éteint la télé (Freebox Player). Bascule l'état actuel.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}


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
        correlation_id = args.get("__correlation_id") or str(uuid.uuid4())
        name = invocation.tool_name

        if name == "channel_up":
            keys = ["prgm_inc"] * _clamp_steps(args.get("steps", 1))
            return self._cmd(CommandAction.set_channel, name, keys, correlation_id)

        if name == "channel_down":
            keys = ["prgm_dec"] * _clamp_steps(args.get("steps", 1))
            return self._cmd(CommandAction.set_channel, name, keys, correlation_id)

        if name == "set_channel":
            keys = list(str(int(args["number"])))  # ex: 26 -> ["2", "6"]
            return self._cmd(CommandAction.set_channel, name, keys, correlation_id,
                             extra={"number": int(args["number"])})

        if name == "volume_up":
            keys = ["vol_inc"] * _clamp_steps(args.get("steps", 3))
            return self._cmd(CommandAction.set_volume, name, keys, correlation_id)

        if name == "volume_down":
            keys = ["vol_dec"] * _clamp_steps(args.get("steps", 3))
            return self._cmd(CommandAction.set_volume, name, keys, correlation_id)

        if name == "mute":
            return self._cmd(CommandAction.set_volume, name, ["mute"], correlation_id)

        if name == "power":
            return self._cmd(CommandAction.on, name, ["power"], correlation_id)

        raise ValueError(f"Tool reconnu mais non câblé dans resolve() : {name!r}")

    @staticmethod
    def _cmd(
        action: CommandAction,
        intent: str,
        keys: list[str],
        correlation_id: str,
        extra: dict[str, Any] | None = None,
    ) -> DeviceCommand:
        params: dict[str, Any] = {"intent": intent, "keys": keys}
        if extra:
            params.update(extra)
        return DeviceCommand(
            device_url=_PLAYER_URL,
            action=action,
            params=params,
            correlation_id=correlation_id,
        )

    # ----------------- execute : DeviceCommand -> ExecutionResult -----------------

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        keys: list[str] = command.params.get("keys", [])
        if not keys:
            return self._failure(command, "Aucune touche à envoyer.")

        # Mode jury / dev OU code absent -> exécution simulée (aucun appel réseau).
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
        """Envoie les touches au Player une par une. Retourne la durée totale (ms)."""
        import requests

        url = f"http://{self._host}/pub/remote_control"
        start = time.monotonic()
        for i, key in enumerate(keys):
            if i:
                time.sleep(_KEY_DELAY_S)
            resp = requests.get(
                url,
                params={"code": self._code, "key": key},
                timeout=_TIMEOUT_S,
            )
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
