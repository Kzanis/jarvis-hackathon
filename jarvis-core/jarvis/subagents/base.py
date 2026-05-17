"""Contrat sous-agent Jarvis.

Tout sous-agent (tahoma, devialet, agenda, ...) implémente le Protocol SubAgent.
Les outils exposés au LLM orchestrateur sont décrits via ToolSpec (Pydantic strict).

Règle absolue : un sous-agent ne fait JAMAIS confiance aux args bruts du LLM.
Il valide via Pydantic (extra="forbid") avant toute action.
"""
from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from jarvis.domain.types import DeviceCommand, ExecutionResult, SensitivityLevel


class ToolSpec(BaseModel):
    """Spécification d'un outil exposé au LLM orchestrateur.

    `params_schema` doit être un JSON Schema STRICT (additionalProperties: false).
    `default_sensitivity` est appliqué au moment du tool_router → DeviceCommand,
    mais le Policy Engine peut élever ce niveau via élévation contextuelle.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=10, max_length=500)
    params_schema: dict[str, Any]
    default_sensitivity: SensitivityLevel
    domain: str = Field(..., min_length=1, max_length=32)


class ToolInvocation(BaseModel):
    """Appel d'outil émis par le LLM orchestrateur (avant résolution)."""

    model_config = ConfigDict(extra="forbid")

    domain: str = Field(..., min_length=1, max_length=32)
    tool_name: str = Field(..., min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class SubAgent(Protocol):
    """Contrat que chaque sous-agent doit respecter.

    Le tool_router :
      1. lit `tools` (registre des ToolSpec exposés)
      2. valide les arguments contre `params_schema` (Pydantic strict)
      3. appelle `resolve()` pour transformer ToolInvocation -> DeviceCommand typée
      4. la DeviceCommand part dans Policy + Audit + Handler (chemin existant)

    `resolve()` est sync (pas d'IO réseau).
    `execute()` est async (alignement avec les handlers existants).
    """

    domain: str
    tools: list[ToolSpec]

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand: ...

    async def execute(self, command: DeviceCommand) -> ExecutionResult: ...


def get_tool_spec(agent: SubAgent, tool_name: str) -> ToolSpec | None:
    """Helper pour retrouver un ToolSpec par son nom dans un sous-agent."""
    for spec in agent.tools:
        if spec.name == tool_name:
            return spec
    return None
