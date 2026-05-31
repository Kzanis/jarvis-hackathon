"""Sous-agent TaHoma : volets, portail, garage, alarme, store, lampes RTS.

Façade autour de TahomaHandler (réel) ou TahomaMock (mock).
Convertit les tool_calls LLM en DeviceCommand validée et délègue l'exécution
au handler choisi selon ExecutionMode (.env).
"""
from __future__ import annotations

import os
import unicodedata
import uuid
from typing import Any, Iterable, Protocol

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    SensitivityLevel,
)
from jarvis.subagents.base import SubAgent, ToolInvocation, ToolSpec


DOMAIN = "tahoma"


# ------------------------------------------------------------------
# Mapping nom logique (LLM) -> identifiant device TaHoma.
# La valeur est SOIT un label TaHoma (résolu en URL au runtime via list_devices),
# SOIT un ID Somfy court et STABLE (cas des deux bureaux : insensible au
# renommage du volet dans l'appli Somfy/TaHoma).
# Source : devices déclarés dans jarvis/mocks/tahoma_mock.py (17 devices).
# Les clefs sont normalisées (sans accents, minuscules, sans espaces).
# ------------------------------------------------------------------
_SHUTTER_ALIASES: dict[str, str] = {
    "salon": "Volet Salon",
    "cuisine": "volet cuisine",
    "sallemanger": "Volet salle a manger",
    "salleamanger": "Volet salle a manger",
    "chambre": "volet chambre",
    # Les deux bureaux -> ID Somfy STABLE (et non label), pour rester corrects
    # même si le volet est renommé dans l'appli Somfy.
    #   1218264 = bureau de Denis  (ex-buanderie, validé 14/05 — volet du cold open)
    #   5922177 = bureau de Muriel (ex-"bureau")
    "bureaudedenis": "1218264",
    "bureaudemuriel": "5922177",
    "salledebain": "volet salle de bain",
    "sdb": "volet salle de bain",
    # Rétro-compatibilité : anciens noms encore acceptés -> même ID stable.
    "buanderie": "1218264",
    "bureau": "5922177",
}

_AWNING_ALIAS = "store banne"
_GATE_ALIAS = "Portail"  # moteur RTS "Evolvia" renommé "Portail" dans TaHoma
_GARAGE_ALIAS = "porte garage"
_LIGHT_RTS_ALIAS = "Douille télécommandée RTS"

_ALARM_ZONES: dict[str, str] = {
    "all": "GMDE_Zone1",  # zone par défaut V1, V2 = multi-zones
    "zone1": "GMDE_Zone1",
    "zone2": "GMDE_Zone2",
    "perimeter": "GMDE_Zone1",
    "night": "GMDE_Zone2",
}


def _normalize_key(value: str) -> str:
    """Normalise un nom utilisateur : enlève accents, espaces, met en minuscules."""
    nfkd = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_only.replace(" ", "").replace("-", "").replace("_", "").lower()


# ------------------------------------------------------------------
# Registre des tools exposés au LLM orchestrateur
# ------------------------------------------------------------------
TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="list_devices",
        description="Liste tous les devices TaHoma disponibles (volets, portail, garage, alarme).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="open_shutter",
        description=(
            "Ouvre un volet roulant désigné par son nom logique "
            "(bureau_de_denis, bureau_de_muriel, salon, cuisine, chambre, "
            "salle_de_bain, salle_a_manger). "
            "« le bureau de Denis » -> bureau_de_denis ; "
            "« le bureau de Muriel » -> bureau_de_muriel."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["shutter_name"],
            "properties": {
                "shutter_name": {"type": "string", "minLength": 1, "maxLength": 32}
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="close_shutter",
        description=(
            "Ferme un volet roulant désigné par son nom logique "
            "(bureau_de_denis, bureau_de_muriel, salon, cuisine, chambre, "
            "salle_de_bain, salle_a_manger). "
            "« le bureau de Denis » -> bureau_de_denis ; "
            "« le bureau de Muriel » -> bureau_de_muriel."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["shutter_name"],
            "properties": {
                "shutter_name": {"type": "string", "minLength": 1, "maxLength": 32}
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="set_shutter_position",
        description="Positionne un volet à un pourcentage de fermeture (0=ouvert, 100=fermé).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["shutter_name", "closure_percent"],
            "properties": {
                "shutter_name": {"type": "string", "minLength": 1, "maxLength": 32},
                "closure_percent": {"type": "integer", "minimum": 0, "maximum": 100},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="open_all_shutters",
        description="Ouvre tous les volets de la maison (commande groupée).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="close_all_shutters",
        description="Ferme tous les volets de la maison (commande groupée).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="open_gate",
        description="Ouvre le portail extérieur. Action physique sensible.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="close_gate",
        description="Ferme le portail extérieur. Action physique sensible.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="open_garage",
        description="Ouvre la porte de garage. Action physique sensible.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="close_garage",
        description="Ferme la porte de garage. Action physique sensible.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="open_awning",
        description="Déploie le store banne (terrasse).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="close_awning",
        description="Replie le store banne (terrasse).",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="arm_alarm",
        description="Active l'alarme de la maison (zone choisie). Niveau de base : sensible.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "zone": {"type": "string", "enum": ["all", "zone1", "zone2", "night", "perimeter"]}
            },
        },
        default_sensitivity=SensitivityLevel.sensible,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="disarm_alarm",
        description="Désactive l'alarme. CRITIQUE : requiert confirmation + PIN vocal.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "zone": {"type": "string", "enum": ["all", "zone1", "zone2", "night", "perimeter"]}
            },
        },
        default_sensitivity=SensitivityLevel.critique,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="toggle_rts_light",
        description="Allume ou éteint la douille télécommandée RTS.",
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["state"],
            "properties": {
                "state": {"type": "string", "enum": ["on", "off"]}
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}


# ------------------------------------------------------------------
# Protocol des handlers d'exécution (compat handlers réel + mock)
# ------------------------------------------------------------------
class _TahomaExecutor(Protocol):
    async def list_devices(self) -> list[dict[str, Any]]: ...
    async def execute(self, command: DeviceCommand) -> ExecutionResult: ...


# ------------------------------------------------------------------
# Sous-agent
# ------------------------------------------------------------------
class TahomaAgent:
    """Sous-agent TaHoma. Implémente le Protocol SubAgent."""

    domain: str = DOMAIN
    tools: list[ToolSpec] = TOOLS

    def __init__(self, executor: _TahomaExecutor | None = None) -> None:
        if executor is None:
            executor = self._build_default_executor()
        self._executor = executor
        # Cache label TaHoma -> deviceURL court (peuplé au premier list_devices)
        self._label_to_url: dict[str, str] = {}

    @staticmethod
    def _build_default_executor() -> _TahomaExecutor:
        """Choisit handler réel ou mock selon ExecutionMode global."""
        mode = os.getenv("EXECUTION_MODE", "mock").lower()
        if mode == "production":
            from jarvis.handlers.tahoma import TahomaHandler

            ip = os.getenv("TAHOMA_IP", "")
            port = int(os.getenv("TAHOMA_PORT", "8443"))
            token = os.getenv("TAHOMA_TOKEN", "")
            return TahomaHandler(ip=ip, port=port, token=token)

        from jarvis.mocks.tahoma_mock import TahomaMock

        return TahomaMock()

    # ----------------- resolve : ToolInvocation -> DeviceCommand -----------------

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand:
        if invocation.domain != DOMAIN:
            raise ValueError(f"TahomaAgent reçoit un mauvais domaine : {invocation.domain!r}")

        spec = _TOOL_BY_NAME.get(invocation.tool_name)
        if spec is None:
            raise ValueError(
                f"Tool inconnu pour {DOMAIN} : {invocation.tool_name!r}. "
                f"Disponibles : {sorted(_TOOL_BY_NAME)}"
            )

        args = invocation.arguments or {}
        correlation_id = args.get("__correlation_id") or str(uuid.uuid4())

        if invocation.tool_name == "list_devices":
            return DeviceCommand(
                device_url="__catalog__",
                action=CommandAction.speak,
                params={"intent": "list_devices"},
                correlation_id=correlation_id,
            )

        if invocation.tool_name in ("open_shutter", "close_shutter"):
            label = self._resolve_shutter_label(args["shutter_name"])
            action = CommandAction.open if invocation.tool_name == "open_shutter" else CommandAction.close
            return DeviceCommand(
                device_url=label,
                action=action,
                params={},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "set_shutter_position":
            label = self._resolve_shutter_label(args["shutter_name"])
            return DeviceCommand(
                device_url=label,
                action=CommandAction.set_closure,
                params={"value": int(args["closure_percent"])},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "open_all_shutters":
            return DeviceCommand(
                device_url="__group_shutters__",
                action=CommandAction.open,
                params={"group": "all_shutters"},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "close_all_shutters":
            return DeviceCommand(
                device_url="__group_shutters__",
                action=CommandAction.close,
                params={"group": "all_shutters"},
                correlation_id=correlation_id,
            )

        if invocation.tool_name in ("open_gate", "close_gate"):
            action = CommandAction.open if invocation.tool_name == "open_gate" else CommandAction.close
            return DeviceCommand(
                device_url=_GATE_ALIAS,
                action=action,
                params={},
                correlation_id=correlation_id,
            )

        if invocation.tool_name in ("open_garage", "close_garage"):
            action = CommandAction.open if invocation.tool_name == "open_garage" else CommandAction.close
            return DeviceCommand(
                device_url=_GARAGE_ALIAS,
                action=action,
                params={},
                correlation_id=correlation_id,
            )

        if invocation.tool_name in ("open_awning", "close_awning"):
            action = CommandAction.open if invocation.tool_name == "open_awning" else CommandAction.close
            return DeviceCommand(
                device_url=_AWNING_ALIAS,
                action=action,
                params={},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "arm_alarm":
            zone_key = args.get("zone", "all").lower()
            zone_label = _ALARM_ZONES.get(zone_key, _ALARM_ZONES["all"])
            return DeviceCommand(
                device_url=zone_label,
                action=CommandAction.arm,
                params={"zone": zone_key},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "disarm_alarm":
            zone_key = args.get("zone", "all").lower()
            zone_label = _ALARM_ZONES.get(zone_key, _ALARM_ZONES["all"])
            return DeviceCommand(
                device_url=zone_label,
                action=CommandAction.disarm,
                params={"zone": zone_key},
                correlation_id=correlation_id,
            )

        if invocation.tool_name == "toggle_rts_light":
            state = args["state"]
            return DeviceCommand(
                device_url=_LIGHT_RTS_ALIAS,
                action=CommandAction.on if state == "on" else CommandAction.off,
                params={},
                correlation_id=correlation_id,
            )

        raise ValueError(f"Tool reconnu mais non câblé dans resolve() : {invocation.tool_name!r}")

    @staticmethod
    def _resolve_shutter_label(name: str) -> str:
        key = _normalize_key(name)
        if key in _SHUTTER_ALIASES:
            return _SHUTTER_ALIASES[key]
        raise ValueError(
            f"Volet inconnu : {name!r}. Disponibles : {sorted(_SHUTTER_ALIASES)}"
        )

    # ----------------- execute : DeviceCommand -> ExecutionResult -----------------

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        # Catalogue spécial (list_devices)
        if command.device_url == "__catalog__":
            devices = await self._executor.list_devices()
            from jarvis.domain.types import ExecutionStatus
            return ExecutionResult(
                status=ExecutionStatus.success,
                correlation_id=command.correlation_id,
                device_url="__catalog__",
                action=command.action,
                duration_ms=0,
                response={"devices": devices},
            )

        # Commandes groupées (open_all / close_all shutters)
        if command.device_url == "__group_shutters__":
            return await self._execute_group_shutters(command)

        # Commande unitaire : on convertit label -> URL courte
        await self._ensure_url_cache()
        device_url = self._label_to_url.get(command.device_url, command.device_url)
        unitary_command = command.model_copy(update={"device_url": device_url})
        return await self._executor.execute(unitary_command)

    async def _execute_group_shutters(self, command: DeviceCommand) -> ExecutionResult:
        """Exécute la commande sur tous les volets, retourne un résultat agrégé."""
        from jarvis.domain.types import ExecutionStatus
        await self._ensure_url_cache()

        shutter_labels = [label for key, label in _SHUTTER_ALIASES.items()]
        # Dédoublonne (alias multiples pour un même volet)
        seen: set[str] = set()
        unique_labels = []
        for label in shutter_labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)

        results: list[ExecutionResult] = []
        for label in unique_labels:
            device_url = self._label_to_url.get(label, label)
            sub_cmd = DeviceCommand(
                device_url=device_url,
                action=command.action,
                params={},
                correlation_id=command.correlation_id,
            )
            results.append(await self._executor.execute(sub_cmd))

        successes = sum(1 for r in results if r.status == ExecutionStatus.success)
        total = len(results)
        status = (
            ExecutionStatus.success
            if successes == total
            else (ExecutionStatus.partial if successes > 0 else ExecutionStatus.failure)
        )
        total_duration = sum(r.duration_ms for r in results)
        return ExecutionResult(
            status=status,
            correlation_id=command.correlation_id,
            device_url="__group_shutters__",
            action=command.action,
            duration_ms=total_duration,
            response={"total": total, "succeeded": successes},
        )

    async def _ensure_url_cache(self) -> None:
        if self._label_to_url:
            return
        devices = await self._executor.list_devices()
        for d in devices:
            # .strip() : TaHoma autorise des espaces parasites dans les labels
            # (ex: "Portail " avec espace finale) — on normalise pour la résolution.
            label = (d.get("label") or "").strip()
            url = d.get("url") or d.get("deviceURL") or ""
            if "/" in url:
                url = url.split("/")[-1]
            if label and url:
                self._label_to_url[label] = url


def list_shutter_aliases() -> Iterable[str]:
    """Helper : liste des alias volets reconnus (pour debug/tests)."""
    return _SHUTTER_ALIASES.keys()
