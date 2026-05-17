"""Sous-agent Agenda : Google Calendar (lecture + écriture).

V1 hackathon : mode mock par défaut (AgendaMock).
V2 / production : brancher google-api-python-client avec Service Account.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Protocol

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    SensitivityLevel,
)
from jarvis.subagents.base import ToolInvocation, ToolSpec


DOMAIN = "agenda"


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="list_events_today",
        description="Liste les rendez-vous d'aujourd'hui (titre, heure, durée).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="list_events_tomorrow",
        description="Liste les rendez-vous de demain (titre, heure, durée).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="list_events_range",
        description="Liste les rendez-vous sur une plage de dates (max 31 jours).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["start_date", "end_date"],
            "properties": {
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="create_event",
        description="Crée un nouvel événement dans le calendrier principal.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "start", "duration_minutes"],
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "start": {"type": "string", "format": "date-time"},
                "duration_minutes": {"type": "integer", "minimum": 5, "maximum": 1440},
                "location": {"type": "string", "maxLength": 200},
                "description": {"type": "string", "maxLength": 1000},
            },
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="find_slot",
        description="Trouve un créneau libre d'une certaine durée dans une plage de dates.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["duration_minutes", "earliest", "latest"],
            "properties": {
                "duration_minutes": {"type": "integer", "minimum": 5, "maximum": 480},
                "earliest": {"type": "string", "format": "date-time"},
                "latest": {"type": "string", "format": "date-time"},
                "preferred_hours": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0, "maximum": 23},
                    "maxItems": 24,
                },
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}


class _AgendaExecutor(Protocol):
    async def execute(self, command: DeviceCommand) -> ExecutionResult: ...


class AgendaAgent:
    """Sous-agent Agenda Google Calendar (mock V1)."""

    domain: str = DOMAIN
    tools: list[ToolSpec] = TOOLS

    def __init__(self, executor: _AgendaExecutor | None = None) -> None:
        if executor is None:
            executor = self._build_default_executor()
        self._executor = executor

    @staticmethod
    def _build_default_executor() -> _AgendaExecutor:
        mode = os.getenv("EXECUTION_MODE", "mock").lower()
        if mode == "production":
            # V2 : brancher google-api-python-client + Service Account.
            # En attendant on retombe sur le mock pour ne jamais bloquer la démo.
            pass
        from jarvis.mocks.agenda_mock import AgendaMock
        return AgendaMock()

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand:
        if invocation.domain != DOMAIN:
            raise ValueError(f"AgendaAgent reçoit un mauvais domaine : {invocation.domain!r}")

        spec = _TOOL_BY_NAME.get(invocation.tool_name)
        if spec is None:
            raise ValueError(
                f"Tool inconnu pour {DOMAIN} : {invocation.tool_name!r}. "
                f"Disponibles : {sorted(_TOOL_BY_NAME)}"
            )

        args: dict[str, Any] = invocation.arguments or {}
        correlation_id = args.get("__correlation_id") or str(uuid.uuid4())

        # Pour tous les tools agenda, on passe par CommandAction.speak — c'est une
        # opération de lecture/écriture data, pas un actionneur physique.
        params: dict[str, Any] = {"intent": invocation.tool_name, **{k: v for k, v in args.items() if k != "__correlation_id"}}

        return DeviceCommand(
            device_url=f"agenda:{invocation.tool_name}",
            action=CommandAction.speak,
            params=params,
            correlation_id=correlation_id,
        )

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        return await self._executor.execute(command)
