"""
Mock TaHoma — substitut sans réseau, pour le jury et les tests.
Doit passer les mêmes contract tests que le vrai handler.
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


class TahomaMock:
    """Simulateur : log + délai + état interne. Pas de réseau."""

    name = "tahoma"

    def __init__(self) -> None:
        self._devices = [
            {"url": "1454237", "label": "Volet Salon", "type": "Shutter"},
            {"url": "1857717", "label": "volet cuisine", "type": "Shutter"},
            {"url": "11515060", "label": "Volet salle a manger", "type": "Shutter"},
            {"url": "1348289", "label": "volet chambre", "type": "Shutter"},
            {"url": "5922177", "label": "volet bureau", "type": "Shutter"},
            {"url": "7368424", "label": "volet salle de bain", "type": "Shutter"},
            {"url": "1218264", "label": "volet buanderie", "type": "Shutter"},
            {"url": "6137785", "label": "store banne", "type": "Awning"},
            {"url": "16471272", "label": "PORTAIL", "type": "Gate"},
            {"url": "881454", "label": "porte garage", "type": "GarageDoor"},
            {"url": "438974", "label": "GMDE_Zone1", "type": "AlarmZone"},
            {"url": "7745091", "label": "GMDE_Zone2", "type": "AlarmZone"},
            {"url": "16740321", "label": "Douille télécommandée RTS", "type": "Light"},
        ]
        self._state: dict[str, dict[str, Any]] = {
            d["url"]: {"position": 100, "armed": False, "on": False} for d in self._devices
        }
        self.calls: list[dict[str, Any]] = []  # historique pour les tests

    async def list_devices(self) -> list[dict[str, Any]]:
        await asyncio.sleep(0.01)
        return list(self._devices)

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        start = time.perf_counter()
        await asyncio.sleep(0.05)  # simule la latence réseau

        # Mémorise l'appel pour les tests
        self.calls.append({
            "device_url": command.device_url,
            "action": command.action.value,
            "params": command.params,
        })

        # Met à jour l'état interne
        state = self._state.setdefault(command.device_url, {})
        if command.action == CommandAction.open:
            state["position"] = 100
        elif command.action == CommandAction.close:
            state["position"] = 0
        elif command.action == CommandAction.set_closure:
            state["position"] = 100 - int(command.params.get("value", 50))
        elif command.action == CommandAction.on:
            state["on"] = True
        elif command.action == CommandAction.off:
            state["on"] = False
        elif command.action == CommandAction.arm:
            state["armed"] = True
        elif command.action == CommandAction.disarm:
            state["armed"] = False

        duration_ms = int((time.perf_counter() - start) * 1000)
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=command.device_url,
            action=command.action,
            duration_ms=duration_ms,
            response={"mock": True, "new_state": state},
        )

    async def health_check(self) -> bool:
        return True
