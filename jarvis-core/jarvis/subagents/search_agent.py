"""Sous-agent Recherche — réponses factuelles / actualité via le web.

Contrairement aux autres sous-agents (qui pilotent des appareils), celui-ci
RAPPORTE une réponse textuelle : il interroge un modèle Perplexity "sonar"
(recherche web intégrée) via OpenRouter, et renvoie une réponse concise dans
ExecutionResult.response["answer"]. Le CommandRouter fait ensuite prononcer
cette réponse par Jarvis.

Réutilise la clé OPENROUTER_API_KEY déjà en place (aucun compte Perplexity
dédié nécessaire).
"""
from __future__ import annotations

import asyncio
import os
import re
import uuid
from typing import Any

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    ExecutionStatus,
    SensitivityLevel,
)
from jarvis.subagents.base import ToolInvocation, ToolSpec


DOMAIN = "search"
_SEARCH_URL = "__web_search__"

# Modèle Perplexity en ligne via OpenRouter (recherche web intégrée).
_DEFAULT_MODEL = "perplexity/sonar"
_TIMEOUT_S = 18.0

_SYSTEM_PROMPT = (
    "Tu es l'assistant de recherche de Jarvis, un majordome vocal. "
    "On te pose une question ; tu réponds en FRANÇAIS, de façon CONCISE "
    "(2 à 3 phrases maximum), dans un style oral fluide destiné à être lu à "
    "voix haute. Pas de listes, pas de markdown, pas de titres, pas de notes "
    "de bas de page ni de crochets [1]. Va droit au fait. Si l'information "
    "n'est pas trouvable, dis-le simplement."
)


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="web_search",
        description=(
            "Recherche une information sur internet et renvoie une réponse à jour. "
            "À utiliser pour TOUTE question factuelle, d'actualité, de météo, de "
            "définition, de culture générale ou nécessitant des données récentes "
            "(ex : 'quelle météo demain à Fayence ?', 'qui a gagné le match ?', "
            "'c'est quoi le projet X ?'). Ne réponds jamais de mémoire à ce type de "
            "question : utilise cet outil."
        ),
        params_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 400},
            },
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}


class SearchAgent:
    """Sous-agent recherche web. Interroge OpenRouter (modèle sonar) et renvoie la réponse."""

    domain: str = DOMAIN
    tools: list[ToolSpec] = TOOLS

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("SEARCH_MODEL") or _DEFAULT_MODEL

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand:
        if invocation.domain != DOMAIN:
            raise ValueError(f"SearchAgent reçoit un mauvais domaine : {invocation.domain!r}")
        spec = _TOOL_BY_NAME.get(invocation.tool_name)
        if spec is None:
            raise ValueError(
                f"Tool inconnu pour {DOMAIN} : {invocation.tool_name!r}. "
                f"Disponibles : {sorted(_TOOL_BY_NAME)}"
            )
        args: dict[str, Any] = invocation.arguments or {}
        correlation_id = args.get("__correlation_id") or str(uuid.uuid4())
        query = str(args.get("query", "")).strip()
        return DeviceCommand(
            device_url=_SEARCH_URL,
            action=CommandAction.speak,
            params={"intent": "web_search", "query": query},
            correlation_id=correlation_id,
        )

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        query = str(command.params.get("query", "")).strip()
        if not query:
            return ExecutionResult(
                status=ExecutionStatus.failure,
                correlation_id=command.correlation_id,
                device_url=_SEARCH_URL,
                action=command.action,
                error="Requête de recherche vide.",
            )
        try:
            answer = await asyncio.to_thread(self._search_sync, query)
        except Exception as e:  # noqa: BLE001
            return ExecutionResult(
                status=ExecutionStatus.failure,
                correlation_id=command.correlation_id,
                device_url=_SEARCH_URL,
                action=command.action,
                error=f"Recherche indisponible : {type(e).__name__}: {e}",
            )
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=_SEARCH_URL,
            action=command.action,
            response={"intent": "web_search", "query": query, "answer": answer},
        )

    def _search_sync(self, query: str) -> str:
        from openai import OpenAI

        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY manquante")
        client = OpenAI(
            api_key=key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=_TIMEOUT_S,
        )
        resp = client.chat.completions.create(
            model=self._model,
            max_tokens=400,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
        )
        content = (resp.choices[0].message.content or "").strip()
        # Nettoyage pour lecture vocale : sonar ajoute des citations [1][2] et du
        # markdown (**gras**, #titres, `code`) qui se lisent mal à voix haute.
        content = re.sub(r"\[\d+\]", "", content)
        content = re.sub(r"[*_`#]+", "", content)
        content = re.sub(r"[ \t]{2,}", " ", content).strip()
        return content or "Je n'ai rien trouvé de probant, Monsieur."
