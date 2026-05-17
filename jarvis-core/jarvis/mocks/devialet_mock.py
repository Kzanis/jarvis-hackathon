"""Mock Devialet — simule un système audio multi-zones (Freebox Delta + 6 HP intégrés).

Sans réseau. Logue les appels pour les tests. Garde l'état (zone -> {playing, volume, source}).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    ExecutionStatus,
)


_DEFAULT_ZONES = ("salon", "cuisine", "chambre", "bureau", "salle_de_bain")
_DEFAULT_SOURCES = ("spotify", "radio", "tv", "bluetooth")


class DevialetMock:
    """Simulateur Devialet. Implémente la même surface que le futur handler réel."""

    name = "devialet"

    def __init__(self) -> None:
        self._state: dict[str, dict[str, Any]] = {
            zone: {"playing": False, "volume": 30, "source": "radio", "muted": False}
            for zone in _DEFAULT_ZONES
        }
        self.calls: list[dict[str, Any]] = []

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        start = time.perf_counter()
        await asyncio.sleep(0.02)

        zone = command.device_url
        state = self._state.setdefault(
            zone, {"playing": False, "volume": 30, "source": "radio", "muted": False}
        )

        params = dict(command.params or {})
        self.calls.append({
            "device_url": zone,
            "action": command.action.value,
            "params": params,
        })

        intent = params.get("intent", "")

        if intent == "play_zone":
            state["playing"] = True
            if "source" in params:
                state["source"] = params["source"]
            state["muted"] = False
        elif intent == "stop_zone" or command.action == CommandAction.stop:
            state["playing"] = False
        elif intent == "set_volume" and command.action == CommandAction.set_volume:
            state["volume"] = int(params.get("volume", state["volume"]))
            state["muted"] = False
        elif intent == "mute":
            state["muted"] = True
        elif intent == "set_source":
            state["source"] = params.get("source", state["source"])

        duration_ms = int((time.perf_counter() - start) * 1000)
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=zone,
            action=command.action,
            duration_ms=duration_ms,
            response={"mock": True, "new_state": dict(state)},
        )

    async def health_check(self) -> bool:
        return True

    def get_state(self, zone: str) -> dict[str, Any]:
        return dict(self._state.get(zone, {}))
