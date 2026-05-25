"""
Handler TaHoma réel — port d'exécution pur vers la box Somfy.

Ne contient AUCUNE logique de sécurité métier (policy/confirmation/audit).
Refuse de s'instancier si EXECUTION_MODE != production
ou ALLOW_REAL_DEVICES != true (garde-fou anti-accident).

Implémente le Protocol DeviceHandler (jarvis.domain.protocols).
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    ExecutionStatus,
)


class RealDevicesGuard(Exception):
    """Levée si on tente d'instancier le handler réel sans autorisation explicite."""


class TahomaHandler:
    """
    Client HTTP de l'API Local TaHoma (Overkiz Device Server).

    Endpoints utilisés :
        GET  /enduser-mobile-web/1/enduserAPI/setup/devices
        POST /enduser-mobile-web/1/enduserAPI/exec/apply
    """

    name = "tahoma"

    # Mapping action interne → commande TaHoma + params
    _COMMAND_MAP: dict[CommandAction, tuple[str, list]] = {
        CommandAction.open: ("open", []),
        CommandAction.close: ("close", []),
        CommandAction.stop: ("stop", []),
        CommandAction.on: ("on", []),
        CommandAction.off: ("off", []),
        CommandAction.arm: ("alarmZoneOn", []),
        CommandAction.disarm: ("off", []),  # zones GMDE se "désarment" avec off
    }

    def __init__(
        self,
        ip: str,
        port: int,
        token: str,
        timeout: float = 10.0,
        verify_ssl: bool = False,  # TaHoma utilise un cert auto-signé Overkiz
    ):
        # === GARDE-FOU ABSOLU ===
        # Refuse de s'instancier sans les 2 conditions explicites.
        mode = os.getenv("EXECUTION_MODE", "mock").lower()
        allow = os.getenv("ALLOW_REAL_DEVICES", "false").lower()
        if mode != "production" or allow != "true":
            raise RealDevicesGuard(
                "Refus d'instancier TahomaHandler réel : "
                f"EXECUTION_MODE={mode!r} (attendu 'production'), "
                f"ALLOW_REAL_DEVICES={allow!r} (attendu 'true'). "
                "Pour activer le matériel réel, mettre ces 2 variables explicitement dans .env."
            )

        if not ip or not token:
            raise ValueError("ip et token TaHoma obligatoires")

        self.base_url = f"https://{ip}:{port}/enduser-mobile-web/1/enduserAPI"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._url_cache: dict[str, str] = {}  # id court → deviceURL complète
        # Client HTTP persistant (HTTP/1.1 keep-alive + TLS session réutilisée).
        # Gain mesuré : ~250ms par requête sur réseau local.
        self._http: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=self._timeout,
                verify=self._verify_ssl,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=60),
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()

    async def list_devices(self) -> list[dict[str, Any]]:
        c = await self._get_client()
        r = await c.get("/setup/devices")
        r.raise_for_status()
        devices = r.json()
            # Met à jour le cache id court → URL complète
        for d in devices:
            full_url = d.get("deviceURL", "")
            if "/" in full_url:
                short = full_url.split("/")[-1]
                self._url_cache[short] = full_url
        return devices

    def _resolve_url(self, device_url: str) -> str:
        """Convertit 'id court' en URL complète si possible."""
        if "://" in device_url:
            return device_url  # déjà une URL complète
        return self._url_cache.get(device_url, device_url)

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        # Lazy load du catalogue si cache vide (pour résoudre l'URL)
        if not self._url_cache:
            try:
                await self.list_devices()
            except Exception as e:
                return ExecutionResult(
                    status=ExecutionStatus.failure,
                    correlation_id=command.correlation_id,
                    device_url=command.device_url,
                    action=command.action,
                    error=f"Catalogue devices inaccessible : {e}",
                )

        full_url = self._resolve_url(command.device_url)

        if command.action not in self._COMMAND_MAP and command.action != CommandAction.set_closure:
            return ExecutionResult(
                status=ExecutionStatus.failure,
                correlation_id=command.correlation_id,
                device_url=full_url,
                action=command.action,
                error=f"Action non supportée par TaHoma : {command.action.value}",
            )

        # Construit la commande TaHoma
        if command.action == CommandAction.set_closure:
            tahoma_cmd_name = "setClosure"
            tahoma_params = [int(command.params.get("value", 50))]
        else:
            tahoma_cmd_name, tahoma_params = self._COMMAND_MAP[command.action]

        payload = {
            "label": f"Jarvis {command.action.value}",
            "actions": [
                {
                    "deviceURL": full_url,
                    "commands": [
                        {"name": tahoma_cmd_name, "parameters": tahoma_params}
                    ],
                }
            ],
        }

        start = time.perf_counter()
        try:
            c = await self._get_client()
            r = await c.post("/exec/apply", json=payload)
            r.raise_for_status()
            response = r.json()
        except httpx.HTTPStatusError as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return ExecutionResult(
                status=ExecutionStatus.failure,
                correlation_id=command.correlation_id,
                device_url=full_url,
                action=command.action,
                duration_ms=duration_ms,
                error=f"HTTP {e.response.status_code} : {e.response.text[:200]}",
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return ExecutionResult(
                status=ExecutionStatus.failure,
                correlation_id=command.correlation_id,
                device_url=full_url,
                action=command.action,
                duration_ms=duration_ms,
                error=f"{type(e).__name__} : {e}",
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        # On considère la commande réussie dès que la box l'accepte (HTTP 200 + execId).
        # NB : sur l'API locale, l'exécution IO est asynchrone et lente (jusqu'à ~60s
        # pour le garage). Vérifier le mouvement ici bloquerait la réponse vocale ;
        # le bon comportement majordome est de confirmer immédiatement la prise en compte.
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=full_url,
            action=command.action,
            duration_ms=duration_ms,
            response={"exec_id": response.get("execId", ""), "tahoma_command": tahoma_cmd_name},
        )

    async def health_check(self) -> bool:
        try:
            c = await self._get_client()
            r = await c.get("/setup/gateways")
            return r.status_code == 200
        except Exception:
            return False
