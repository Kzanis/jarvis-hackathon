"""Session conversationnelle multi-tours (in-memory).

Mémoire courte qui porte l'historique pour passer plusieurs tours au LLM
sans le recharger à chaque fois. Pas de persistance, pas de DB — c'est
l'état conversationnel "ici et maintenant".

Pour la sécurité critique (PendingConfirmation, PIN), c'est le Policy Engine
qui gère via ConversationContext. Cette session-ci ne gère que la mémoire
conversationnelle utile au LLM.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable


MAX_HISTORY_TURNS = 6           # 3 tours user + 3 tours assistant
SESSION_TTL_SECONDS = 90        # au-delà : on repart de zéro


@dataclass
class ConversationSession:
    """Mémoire courte pour conversation Jarvis ↔ Denis.

    history : liste OpenAI-compatible (role: user|assistant, content: str).
    """

    user_id: str = "denis"
    history: list[dict[str, str]] = field(default_factory=list)
    last_turn_ts: float = field(default_factory=time.time)

    def is_expired(self, now: float | None = None) -> bool:
        now = now or time.time()
        return (now - self.last_turn_ts) > SESSION_TTL_SECONDS

    def reset(self) -> None:
        self.history = []
        self.last_turn_ts = time.time()

    def add_user(self, text: str) -> None:
        self._append({"role": "user", "content": text.strip()})

    def add_assistant(self, spoken_response: str, tool_calls_summary: Iterable[str] = ()) -> None:
        # Pour le LLM, on injecte la réponse parlée. On peut optionnellement
        # ajouter un résumé des tool_calls passés pour la continuité contextuelle.
        content = spoken_response.strip()
        summary = list(tool_calls_summary)
        if summary:
            content = content + f" [actions: {', '.join(summary)}]"
        self._append({"role": "assistant", "content": content})

    def _append(self, message: dict[str, str]) -> None:
        if self.is_expired():
            self.history = []
        self.history.append(message)
        # Garde uniquement les MAX_HISTORY_TURNS derniers tours
        if len(self.history) > MAX_HISTORY_TURNS:
            self.history = self.history[-MAX_HISTORY_TURNS:]
        self.last_turn_ts = time.time()

    def as_llm_history(self) -> list[dict[str, str]]:
        """Retourne l'historique prêt pour LLMOrchestrator.plan_in_conversation()."""
        if self.is_expired():
            return []
        return list(self.history)
