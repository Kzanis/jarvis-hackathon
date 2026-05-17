"""Mock Google Calendar — événements fictifs cohérents pour la démo jury.

Pas d'OAuth, pas de réseau. Implémente la même surface que le futur
AgendaHandler basé sur google-api-python-client.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import date, datetime, time as _time, timedelta
from typing import Any

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    ExecutionStatus,
)


def _today() -> date:
    return datetime.now().date()


class AgendaMock:
    """10 événements fictifs cohérents, lecture et écriture en mémoire."""

    name = "agenda"

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = self._seed_events()
        self.calls: list[dict[str, Any]] = []

    def _seed_events(self) -> list[dict[str, Any]]:
        d = _today()
        return [
            {
                "id": "evt-001",
                "title": "Atelier Tom (Creator Academy)",
                "start": datetime.combine(d, _time(19, 0)),
                "duration_minutes": 90,
                "location": "Zoom",
            },
            {
                "id": "evt-002",
                "title": "Appel client Tur Façadier",
                "start": datetime.combine(d, _time(10, 0)),
                "duration_minutes": 30,
                "location": "Téléphone",
            },
            {
                "id": "evt-003",
                "title": "Revue PRD Jarvis",
                "start": datetime.combine(d + timedelta(days=1), _time(14, 0)),
                "duration_minutes": 60,
                "location": "Bureau",
            },
            {
                "id": "evt-004",
                "title": "Démo Dynaren R1",
                "start": datetime.combine(d + timedelta(days=4), _time(11, 0)),
                "duration_minutes": 60,
                "location": "Visio",
            },
            {
                "id": "evt-005",
                "title": "Networking Academy",
                "start": datetime.combine(d + timedelta(days=8), _time(18, 30)),
                "duration_minutes": 120,
                "location": "Online",
            },
            {
                "id": "evt-006",
                "title": "Chantier ASL Rouquaire — point hebdo",
                "start": datetime.combine(d + timedelta(days=2), _time(9, 0)),
                "duration_minutes": 45,
                "location": "Site",
            },
            {
                "id": "evt-007",
                "title": "DevWithMe #2 (Tylian)",
                "start": datetime.combine(d + timedelta(days=11), _time(20, 0)),
                "duration_minutes": 60,
                "location": "Zoom",
            },
        ]

    async def list_devices(self) -> list[dict[str, Any]]:
        # Pas pertinent pour l'agenda, mais maintien du contrat unique.
        return []

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        start = time.perf_counter()
        await asyncio.sleep(0.01)
        intent = command.params.get("intent", "")
        self.calls.append({"intent": intent, "params": dict(command.params)})

        if intent == "list_events_today":
            d = _today()
            events = [e for e in self._events if e["start"].date() == d]
            return self._ok(command, start, {"events": [self._serialize(e) for e in events]})

        if intent == "list_events_tomorrow":
            d = _today() + timedelta(days=1)
            events = [e for e in self._events if e["start"].date() == d]
            return self._ok(command, start, {"events": [self._serialize(e) for e in events]})

        if intent == "list_events_range":
            start_date = date.fromisoformat(command.params["start_date"])
            end_date = date.fromisoformat(command.params["end_date"])
            events = [
                e for e in self._events
                if start_date <= e["start"].date() <= end_date
            ]
            return self._ok(command, start, {"events": [self._serialize(e) for e in events]})

        if intent == "create_event":
            new = {
                "id": f"evt-{uuid.uuid4().hex[:6]}",
                "title": command.params["title"],
                "start": datetime.fromisoformat(command.params["start"]),
                "duration_minutes": int(command.params["duration_minutes"]),
                "location": command.params.get("location", ""),
                "description": command.params.get("description", ""),
            }
            self._events.append(new)
            return self._ok(command, start, {"event": self._serialize(new)})

        if intent == "find_slot":
            slot = self._find_slot(
                duration_minutes=int(command.params["duration_minutes"]),
                earliest=datetime.fromisoformat(command.params["earliest"]),
                latest=datetime.fromisoformat(command.params["latest"]),
                preferred_hours=command.params.get("preferred_hours") or [],
            )
            return self._ok(command, start, {"slot": slot})

        # Inconnu
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ExecutionResult(
            status=ExecutionStatus.failure,
            correlation_id=command.correlation_id,
            device_url=command.device_url,
            action=command.action,
            duration_ms=duration_ms,
            error=f"intent agenda inconnu : {intent!r}",
        )

    def _ok(self, command: DeviceCommand, start: float, response: dict[str, Any]) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=command.device_url,
            action=command.action,
            duration_ms=int((time.perf_counter() - start) * 1000),
            response=response,
        )

    @staticmethod
    def _serialize(event: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": event["id"],
            "title": event["title"],
            "start": event["start"].isoformat(),
            "duration_minutes": event["duration_minutes"],
            "location": event.get("location", ""),
        }

    def _find_slot(
        self,
        duration_minutes: int,
        earliest: datetime,
        latest: datetime,
        preferred_hours: list[int],
    ) -> dict[str, Any] | None:
        # Recherche naïve par pas de 30 min. Ignore les conflits dans préférences.
        step = timedelta(minutes=30)
        delta = timedelta(minutes=duration_minutes)
        cursor = earliest
        while cursor + delta <= latest:
            if preferred_hours and cursor.hour not in preferred_hours:
                cursor += step
                continue
            conflict = any(
                e["start"] < cursor + delta
                and e["start"] + timedelta(minutes=e["duration_minutes"]) > cursor
                for e in self._events
            )
            if not conflict:
                return {
                    "start": cursor.isoformat(),
                    "end": (cursor + delta).isoformat(),
                }
            cursor += step
        return None

    async def health_check(self) -> bool:
        return True
