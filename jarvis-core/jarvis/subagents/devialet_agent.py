"""Sous-agent Devialet : son maison (Freebox Delta + 6 HP intégrés, multi-zones).

Façade autour de DevialetMock (V1) ou DevialetHandler réel (V2 via PyPI devialet 1.5.7).
"""
from __future__ import annotations

import os
import unicodedata
import uuid
from typing import Any, Protocol

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    SensitivityLevel,
)
from jarvis.subagents.base import ToolInvocation, ToolSpec


DOMAIN = "devialet"

_ZONE_ALIASES: dict[str, str] = {
    "salon": "salon",
    "sejour": "salon",
    "cuisine": "cuisine",
    "chambre": "chambre",
    "bureau": "bureau",
    "salledebain": "salle_de_bain",
    "sdb": "salle_de_bain",
    "all": "salon",  # V1 : fallback salon. V2 : group multi-zone.
}

_SOURCE_ALIASES: dict[str, str] = {
    "spotify": "spotify",
    "musique": "spotify",
    "music": "spotify",
    "radio": "radio",
    "fip": "radio",
    "tv": "tv",
    "television": "tv",
    "bluetooth": "bluetooth",
    "bt": "bluetooth",
}


def _normalize(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_only.replace(" ", "").replace("-", "").replace("_", "").lower()


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="play_zone",
        description="Lance la lecture audio dans une zone (salon, cuisine, etc.) avec une source.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["zone"],
            "properties": {
                "zone": {"type": "string", "minLength": 1, "maxLength": 32},
                "source": {"type": "string", "enum": ["spotify", "radio", "tv", "bluetooth"]},
                "playlist_hint": {"type": "string", "maxLength": 100},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="stop_zone",
        description="Arrête la lecture audio dans une zone.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["zone"],
            "properties": {
                "zone": {"type": "string", "minLength": 1, "maxLength": 32},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="set_volume",
        description="Règle le volume d'une zone (0-100).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["zone", "volume"],
            "properties": {
                "zone": {"type": "string", "minLength": 1, "maxLength": 32},
                "volume": {"type": "integer", "minimum": 0, "maximum": 100},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="mute",
        description="Coupe le son d'une zone.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["zone"],
            "properties": {
                "zone": {"type": "string", "minLength": 1, "maxLength": 32},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="set_source",
        description="Change la source audio d'une zone sans changer le volume.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["zone", "source"],
            "properties": {
                "zone": {"type": "string", "minLength": 1, "maxLength": 32},
                "source": {"type": "string", "enum": ["spotify", "radio", "tv", "bluetooth"]},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}


class _DevialetExecutor(Protocol):
    async def execute(self, command: DeviceCommand) -> ExecutionResult: ...


class DevialetAgent:
    """Sous-agent Devialet."""

    domain: str = DOMAIN
    tools: list[ToolSpec] = TOOLS

    def __init__(self, executor: _DevialetExecutor | None = None) -> None:
        if executor is None:
            executor = self._build_default_executor()
        self._executor = executor

    @staticmethod
    def _build_default_executor() -> _DevialetExecutor:
        # V1 hackathon : mode mock par défaut (handler réel = V2).
        mode = os.getenv("EXECUTION_MODE", "mock").lower()
        allow = os.getenv("ALLOW_REAL_DEVICES", "false").lower()
        if mode == "production" and allow == "true":
            # V2 placeholder : on retombera sur le mock tant qu'aucun handler réel
            # Devialet n'est implémenté (PyPI 'devialet' 1.5.7, à intégrer plus tard).
            pass
        from jarvis.mocks.devialet_mock import DevialetMock
        return DevialetMock()

    def _resolve_zone(self, name: str) -> str:
        key = _normalize(name)
        return _ZONE_ALIASES.get(key, _normalize(name))

    def _resolve_source(self, name: str) -> str:
        key = _normalize(name)
        return _SOURCE_ALIASES.get(key, key)

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand:
        if invocation.domain != DOMAIN:
            raise ValueError(f"DevialetAgent reçoit un mauvais domaine : {invocation.domain!r}")

        spec = _TOOL_BY_NAME.get(invocation.tool_name)
        if spec is None:
            raise ValueError(
                f"Tool inconnu pour {DOMAIN} : {invocation.tool_name!r}. "
                f"Disponibles : {sorted(_TOOL_BY_NAME)}"
            )

        args: dict[str, Any] = invocation.arguments or {}
        correlation_id = args.get("__correlation_id") or str(uuid.uuid4())
        zone = self._resolve_zone(args.get("zone", "salon"))

        if invocation.tool_name == "play_zone":
            params: dict[str, Any] = {"intent": "play_zone", "zone": zone}
            if "source" in args:
                params["source"] = self._resolve_source(args["source"])
            if "playlist_hint" in args:
                params["playlist_hint"] = args["playlist_hint"]
            return DeviceCommand(
                device_url=zone,
                action=CommandAction.on,
                params=params,
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "stop_zone":
            return DeviceCommand(
                device_url=zone,
                action=CommandAction.stop,
                params={"intent": "stop_zone", "zone": zone},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "set_volume":
            return DeviceCommand(
                device_url=zone,
                action=CommandAction.set_volume,
                params={"intent": "set_volume", "zone": zone, "volume": int(args["volume"])},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "mute":
            return DeviceCommand(
                device_url=zone,
                action=CommandAction.set_volume,
                params={"intent": "mute", "zone": zone, "volume": 0},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "set_source":
            return DeviceCommand(
                device_url=zone,
                action=CommandAction.on,
                params={
                    "intent": "set_source",
                    "zone": zone,
                    "source": self._resolve_source(args["source"]),
                },
                correlation_id=correlation_id,
            )

        raise ValueError(f"Tool reconnu mais non câblé : {invocation.tool_name!r}")

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        return await self._executor.execute(command)
