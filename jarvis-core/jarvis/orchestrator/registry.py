"""Registre allowlisté des sous-agents disponibles.

GARDE-FOU CRITIQUE : le LLM orchestrateur ne peut JAMAIS appeler un handler Python
directement. Il référence (domain, tool_name). Le registry valide la paire avant
toute résolution. Toute paire absente du registry = REJECT + audit log "hallucination".
"""
from __future__ import annotations

from typing import Iterable

from jarvis.subagents.base import SubAgent, ToolSpec


class SubAgentRegistry:
    """Registre central des sous-agents et de leurs outils.

    Construit au démarrage de l'orchestrateur. Immutable après construction.
    """

    def __init__(self, agents: Iterable[SubAgent]) -> None:
        self._agents: dict[str, SubAgent] = {}
        self._tools_index: dict[tuple[str, str], ToolSpec] = {}
        for agent in agents:
            if agent.domain in self._agents:
                raise ValueError(f"Domaine sous-agent dupliqué : {agent.domain}")
            self._agents[agent.domain] = agent
            for tool in agent.tools:
                if tool.domain != agent.domain:
                    raise ValueError(
                        f"Incohérence : tool {tool.name} déclare domaine "
                        f"{tool.domain!r} mais l'agent est {agent.domain!r}"
                    )
                key = (agent.domain, tool.name)
                if key in self._tools_index:
                    raise ValueError(f"Outil dupliqué : {key}")
                self._tools_index[key] = tool

    def get_agent(self, domain: str) -> SubAgent:
        if domain not in self._agents:
            raise KeyError(f"Domaine inconnu (hors registry) : {domain!r}")
        return self._agents[domain]

    def get_tool(self, domain: str, tool_name: str) -> ToolSpec:
        key = (domain, tool_name)
        if key not in self._tools_index:
            raise KeyError(
                f"Outil hors registry (hallucination LLM ?) : {domain}/{tool_name}"
            )
        return self._tools_index[key]

    def all_tools(self) -> list[ToolSpec]:
        """Pour construire le prompt système (liste des tools exposés au LLM)."""
        return list(self._tools_index.values())

    def domains(self) -> list[str]:
        return list(self._agents.keys())


def build_default_registry() -> SubAgentRegistry:
    """Construit le registre V1 (tahoma + devialet + agenda).

    À FAIRE 22/05 : brancher en mode production vs mock selon ExecutionMode.
    """
    from jarvis.subagents.agenda_agent import AgendaAgent
    from jarvis.subagents.devialet_agent import DevialetAgent
    from jarvis.subagents.tahoma_agent import TahomaAgent

    return SubAgentRegistry([TahomaAgent(), DevialetAgent(), AgendaAgent()])
