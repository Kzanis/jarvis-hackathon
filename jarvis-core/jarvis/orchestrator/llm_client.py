"""Client LLM orchestrateur — façade multi-provider.

Le LLM PROPOSE des ToolInvocation depuis le texte transcrit (Whisper).
Il n'exécute JAMAIS. Le Policy Engine + le ToolRouter valident avant exécution.

Providers supportés :
- ``openrouter`` (par défaut) : proxy OpenRouter, accès Claude Haiku 4.5 et autres.
                                Format API = compatible OpenAI Chat Completions.
- ``anthropic``               : Anthropic API direct (si crédits disponibles).
- ``openai``                  : OpenAI direct (si clé valide).

Choix provider via env :
    LLM_PROVIDER=openrouter            # défaut
    LLM_MODEL=anthropic/claude-haiku-4.5
    OPENROUTER_API_KEY=...

Verdict Codex 17/05 : Haiku 4.5 primaire, Sonnet 4.6 fallback, pas de LLM local.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jarvis.orchestrator.registry import SubAgentRegistry
from jarvis.subagents.base import ToolInvocation, ToolSpec


DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL_BY_PROVIDER: dict[str, str] = {
    "openrouter": "anthropic/claude-haiku-4.5",
    "anthropic": "claude-haiku-4-5",
    "openai": "gpt-4o-mini",
}
DEFAULT_FALLBACK_MODEL_BY_PROVIDER: dict[str, str] = {
    "openrouter": "anthropic/claude-sonnet-4.5",
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
}

LLM_TIMEOUT_SECONDS = 10
LLM_MAX_TOKENS = 1024


@dataclass(frozen=True)
class PlanResult:
    """Résultat d'un plan LLM : 0+ invocations d'outils + phrase majordome."""

    invocations: list[ToolInvocation]
    spoken_response: str
    model_used: str
    provider_used: str
    latency_ms: int
    stop_reason: str
    input_tokens: int
    output_tokens: int


class LLMUnavailable(Exception):
    """LLM injoignable, timeout, ou erreur API."""


def load_dotenv_if_present() -> None:
    """Charge .env de jarvis-core (parser minimaliste, pas de dépendance).

    Idempotent : ne remplace pas une variable déjà définie dans l'environnement.
    """
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        value = raw_value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


class LLMOrchestrator:
    """Planificateur LLM. Propose des ToolInvocation, n'exécute jamais."""

    def __init__(
        self,
        registry: SubAgentRegistry,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        system_prompt_path: str | Path | None = None,
        timeout_seconds: float = LLM_TIMEOUT_SECONDS,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> None:
        self._registry = registry
        self._provider = (provider or os.getenv("LLM_PROVIDER") or DEFAULT_PROVIDER).lower()
        self._model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL_BY_PROVIDER.get(
            self._provider, "anthropic/claude-haiku-4.5"
        )
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens

        # Sélection du client en fonction du provider
        self._client, self._format = self._build_client(api_key=api_key, base_url=base_url)

        # System prompt majordome
        if system_prompt_path is None:
            system_prompt_path = (
                Path(__file__).resolve().parents[2]
                / "config"
                / "prompts"
                / "personality.md"
            )
        self._system_prompt = Path(system_prompt_path).read_text(encoding="utf-8")

        # Conversion ToolSpec -> tools API (format OpenAI ou Anthropic selon provider)
        self._tools = self._build_tools(registry.all_tools())

    # ------------------------------------------------------------------
    # Construction du client provider-spécifique
    # ------------------------------------------------------------------

    def _build_client(self, api_key: str | None, base_url: str | None) -> tuple[Any, str]:
        """Retourne (client, format_api).

        format_api in {'openai', 'anthropic'}.
        """
        if self._provider == "openrouter":
            from openai import OpenAI

            key = api_key or os.getenv("OPENROUTER_API_KEY")
            if not key:
                raise ValueError("OPENROUTER_API_KEY manquante")
            client = OpenAI(
                api_key=key,
                base_url=base_url or "https://openrouter.ai/api/v1",
                timeout=self._timeout,
            )
            return client, "openai"

        if self._provider == "openai":
            from openai import OpenAI

            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY manquante")
            client = OpenAI(api_key=key, timeout=self._timeout)
            return client, "openai"

        if self._provider == "anthropic":
            import anthropic

            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError("ANTHROPIC_API_KEY manquante")
            client = anthropic.Anthropic(api_key=key, timeout=self._timeout)
            return client, "anthropic"

        raise ValueError(f"Provider LLM inconnu : {self._provider!r}")

    # ------------------------------------------------------------------
    # Construction des tools (format-spécifique)
    # ------------------------------------------------------------------

    def _build_tools(self, specs: list[ToolSpec]) -> list[dict[str, Any]]:
        if self._format == "openai":
            return [
                {
                    "type": "function",
                    "function": {
                        "name": f"{spec.domain}__{spec.name}",
                        "description": spec.description,
                        "parameters": spec.params_schema,
                    },
                }
                for spec in specs
            ]
        # Format Anthropic natif
        return [
            {
                "name": f"{spec.domain}__{spec.name}",
                "description": spec.description,
                "input_schema": spec.params_schema,
            }
            for spec in specs
        ]

    @staticmethod
    def _split_tool_name(name: str) -> tuple[str, str]:
        if "__" not in name:
            raise ValueError(f"Nom tool mal formé (attendu domain__tool) : {name!r}")
        domain, _, tool = name.partition("__")
        return domain, tool

    # ------------------------------------------------------------------
    # plan() : texte -> ToolInvocation[] + phrase majordome
    # ------------------------------------------------------------------

    def plan(
        self,
        transcribed_text: str,
        context: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> PlanResult:
        """Plan single-turn. Pour conversation multi-tours, voir plan_in_conversation."""
        if not transcribed_text or not transcribed_text.strip():
            raise ValueError("transcribed_text vide")

        active_model = model or self._model
        user_text = transcribed_text.strip()
        if context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in context.items())
            user_text = f"[contexte: {ctx_str}]\n{user_text}"

        history: list[dict[str, str]] = [{"role": "user", "content": user_text}]
        if self._format == "openai":
            return self._plan_openai(active_model, history)
        return self._plan_anthropic(active_model, history)

    def plan_in_conversation(
        self,
        history: list[dict[str, str]],
        new_user_text: str,
        model: str | None = None,
    ) -> PlanResult:
        """Plan multi-tours. `history` = [{role, content}, ...] tours précédents.

        L'orchestrateur appelant garde la session en mémoire (ConversationSession).
        On retourne le PlanResult ; l'appelant met à jour son history.
        """
        if not new_user_text or not new_user_text.strip():
            raise ValueError("new_user_text vide")

        active_model = model or self._model
        full_history = list(history) + [{"role": "user", "content": new_user_text.strip()}]
        if self._format == "openai":
            return self._plan_openai(active_model, full_history)
        return self._plan_anthropic(active_model, full_history)

    def _plan_openai(self, active_model: str, history: list[dict[str, str]]) -> PlanResult:
        """Compatible OpenAI Chat Completions (OpenRouter inclus)."""
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        start = time.perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=active_model,
                max_tokens=self._max_tokens,
                tools=self._tools,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    *history,
                ],
            )
        except APITimeoutError as e:
            raise LLMUnavailable(f"Timeout LLM ({self._timeout}s)") from e
        except APIConnectionError as e:
            raise LLMUnavailable(f"Connexion LLM impossible : {e}") from e
        except APIStatusError as e:
            raise LLMUnavailable(
                f"Erreur API LLM {e.status_code} : {getattr(e, 'message', '')}"
            ) from e

        latency_ms = int((time.perf_counter() - start) * 1000)
        choice = response.choices[0]
        message = choice.message

        spoken_response = (message.content or "").strip()
        invocations: list[ToolInvocation] = []
        for tc in (message.tool_calls or []):
            fn = tc.function
            domain, tool_name = self._split_tool_name(fn.name)
            try:
                args = json.loads(fn.arguments) if fn.arguments else {}
            except json.JSONDecodeError:
                args = {}
            invocations.append(
                ToolInvocation(domain=domain, tool_name=tool_name, arguments=args)
            )

        usage = response.usage
        return PlanResult(
            invocations=invocations,
            spoken_response=spoken_response,
            model_used=getattr(response, "model", active_model) or active_model,
            provider_used=self._provider,
            latency_ms=latency_ms,
            stop_reason=choice.finish_reason or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )

    def _plan_anthropic(self, active_model: str, history: list[dict[str, str]]) -> PlanResult:
        """API Anthropic native (tool_use + cache_control)."""
        import anthropic

        start = time.perf_counter()
        try:
            response = self._client.messages.create(
                model=active_model,
                max_tokens=self._max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": self._system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=self._tools,
                messages=history,
            )
        except anthropic.APITimeoutError as e:
            raise LLMUnavailable(f"Timeout Anthropic ({self._timeout}s)") from e
        except anthropic.APIConnectionError as e:
            raise LLMUnavailable(f"Connexion Anthropic impossible : {e}") from e
        except anthropic.APIStatusError as e:
            raise LLMUnavailable(
                f"Erreur API Anthropic {e.status_code} : {getattr(e, 'message', '')}"
            ) from e

        latency_ms = int((time.perf_counter() - start) * 1000)
        invocations: list[ToolInvocation] = []
        spoken_parts: list[str] = []
        for block in response.content:
            t = getattr(block, "type", None)
            if t == "text":
                txt = getattr(block, "text", "").strip()
                if txt:
                    spoken_parts.append(txt)
            elif t == "tool_use":
                domain, tool_name = self._split_tool_name(block.name)
                args = dict(getattr(block, "input", {}) or {})
                invocations.append(
                    ToolInvocation(domain=domain, tool_name=tool_name, arguments=args)
                )

        usage = getattr(response, "usage", None)
        return PlanResult(
            invocations=invocations,
            spoken_response=" ".join(spoken_parts).strip(),
            model_used=active_model,
            provider_used=self._provider,
            latency_ms=latency_ms,
            stop_reason=getattr(response, "stop_reason", "") or "",
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )
