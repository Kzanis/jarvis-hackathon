"""Routeur tool_call LLM -> DeviceCommand validée.

Étape critique sécurité : ici on REJETTE toute hallucination LLM
(domaine inconnu, outil inconnu, args invalides, budget dépassé)
AVANT que la commande n'atteigne le Policy Engine.

Validation des arguments sans dépendance externe : on parcourt le JSON Schema
de chaque ToolSpec (subset suffisant pour notre usage : type, required,
additionalProperties, enum, minLength, maxLength, minimum, maximum, items).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jarvis.domain.types import DeviceCommand, SensitivityLevel
from jarvis.orchestrator.registry import SubAgentRegistry
from jarvis.subagents.base import ToolInvocation, ToolSpec


# ----------------------------------------------------------------------
# Budgets par requête (Codex 17/05)
# ----------------------------------------------------------------------
MAX_TOOL_CALLS_PER_REQUEST = 5
MAX_CRITICAL_CALLS_PER_REQUEST = 1
MAX_SENSIBLE_CALLS_PER_REQUEST = 3


@dataclass(frozen=True)
class RoutedCommand:
    """DeviceCommand résolue + métadonnées (sensibilité par défaut, domaine, tool)."""

    command: DeviceCommand
    domain: str
    tool_name: str
    default_sensitivity: SensitivityLevel


class ToolRouterRejection(Exception):
    """Rejet à l'étape router (avant Policy)."""

    def __init__(self, reason: str, invocation: ToolInvocation | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.invocation = invocation


# ----------------------------------------------------------------------
# Validation JSON Schema (subset)
# ----------------------------------------------------------------------

_PY_TYPE_BY_JSON: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def _validate_schema(schema: dict[str, Any], value: Any, path: str = "$") -> None:
    """Valide value contre schema (subset JSON Schema). Lève ValueError sinon."""
    if not isinstance(schema, dict):
        return

    expected_type = schema.get("type")
    if expected_type:
        py_type = _PY_TYPE_BY_JSON.get(expected_type)
        if py_type is None:
            raise ValueError(f"{path}: type JSON Schema non géré : {expected_type!r}")
        # bool est une sous-classe de int en Python — on évite que True passe pour 1
        if expected_type == "integer" and isinstance(value, bool):
            raise ValueError(f"{path}: integer attendu, bool fourni")
        if expected_type == "number" and isinstance(value, bool):
            raise ValueError(f"{path}: number attendu, bool fourni")
        if not isinstance(value, py_type):
            raise ValueError(
                f"{path}: type {expected_type!r} attendu, obtenu {type(value).__name__}"
            )

    if expected_type == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path}: longueur min {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{path}: longueur max {schema['maxLength']}")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: valeur hors enum {schema['enum']}")

    if expected_type in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}: > maximum {schema['maximum']}")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: valeur hors enum {schema['enum']}")

    if expected_type == "array":
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                _validate_schema(items_schema, item, f"{path}[{i}]")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{path}: > maxItems {schema['maxItems']}")
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(f"{path}: < minItems {schema['minItems']}")

    if expected_type == "object" or "properties" in schema:
        if not isinstance(value, dict):
            raise ValueError(f"{path}: object attendu, obtenu {type(value).__name__}")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional = schema.get("additionalProperties", True)

        for req in required:
            if req not in value:
                raise ValueError(f"{path}.{req}: champ requis manquant")

        for key, sub_value in value.items():
            if key in properties:
                _validate_schema(properties[key], sub_value, f"{path}.{key}")
            else:
                if additional is False:
                    raise ValueError(f"{path}.{key}: clé non autorisée (additionalProperties=false)")


# ----------------------------------------------------------------------
# ToolRouter
# ----------------------------------------------------------------------

class ToolRouter:
    """Convertit les invocations LLM en RoutedCommand prêtes pour le Policy Engine."""

    def __init__(self, registry: SubAgentRegistry) -> None:
        self._registry = registry

    def route_batch(self, invocations: list[ToolInvocation]) -> list[RoutedCommand]:
        if not invocations:
            return []

        if len(invocations) > MAX_TOOL_CALLS_PER_REQUEST:
            raise ToolRouterRejection(
                f"Budget dépassé : {len(invocations)} > max {MAX_TOOL_CALLS_PER_REQUEST} commandes/requête"
            )

        routed: list[RoutedCommand] = []
        critical_count = 0
        sensible_count = 0

        for inv in invocations:
            # 1. domaine connu ?
            try:
                agent = self._registry.get_agent(inv.domain)
            except KeyError as e:
                raise ToolRouterRejection(
                    f"Domaine hors registry (hallucination LLM ?) : {inv.domain!r}",
                    invocation=inv,
                ) from e

            # 2. tool connu ?
            try:
                spec = self._registry.get_tool(inv.domain, inv.tool_name)
            except KeyError as e:
                raise ToolRouterRejection(
                    f"Outil hors registry (hallucination LLM ?) : {inv.domain}/{inv.tool_name}",
                    invocation=inv,
                ) from e

            # 3. arguments valides ?
            try:
                _validate_schema(spec.params_schema, inv.arguments or {})
            except ValueError as e:
                raise ToolRouterRejection(
                    f"Arguments invalides pour {inv.domain}/{inv.tool_name} : {e}",
                    invocation=inv,
                ) from e

            # 4. budgets cumulés (avant resolve)
            if spec.default_sensitivity == SensitivityLevel.critique:
                critical_count += 1
                if critical_count > MAX_CRITICAL_CALLS_PER_REQUEST:
                    raise ToolRouterRejection(
                        f"Budget critique dépassé : > {MAX_CRITICAL_CALLS_PER_REQUEST} action critique/requête",
                        invocation=inv,
                    )
            elif spec.default_sensitivity == SensitivityLevel.sensible:
                sensible_count += 1
                if sensible_count > MAX_SENSIBLE_CALLS_PER_REQUEST:
                    raise ToolRouterRejection(
                        f"Budget sensible dépassé : > {MAX_SENSIBLE_CALLS_PER_REQUEST} actions sensibles/requête",
                        invocation=inv,
                    )

            # 5. resolve (sous-agent)
            try:
                command = agent.resolve(inv)
            except (ValueError, KeyError) as e:
                raise ToolRouterRejection(
                    f"Résolution échouée pour {inv.domain}/{inv.tool_name} : {e}",
                    invocation=inv,
                ) from e

            routed.append(
                RoutedCommand(
                    command=command,
                    domain=inv.domain,
                    tool_name=inv.tool_name,
                    default_sensitivity=spec.default_sensitivity,
                )
            )

        return routed
