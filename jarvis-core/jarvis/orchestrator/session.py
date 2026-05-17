"""Session conversationnelle multi-tours (in-memory).

Mémoire courte qui porte l'historique LLM + un éventuel **batch en attente**
de confirmation orale (PRD §9.4). Le batch pending bloque l'exécution tant
que Denis n'a pas confirmé "oui" (ou n'a pas annulé / fait expirer).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable


MAX_HISTORY_TURNS = 6           # 3 tours user + 3 tours assistant
SESSION_TTL_SECONDS = 90        # au-delà : on repart de zéro
PENDING_TTL_SECONDS = 15        # PRD §9.4 — la confirmation expire en 15s


@dataclass
class PendingBatch:
    """Batch de RoutedCommand en attente de confirmation orale.

    `routed_commands` est typé `list[Any]` ici pour éviter une dépendance
    circulaire vers `tool_router.RoutedCommand`. Le CommandRouter remplit
    et consomme ce champ.
    """

    routed_commands: list[Any] = field(default_factory=list)
    sensitivity_max: str = "sensible"   # "sensible" | "critique"
    speak_question: str = ""             # phrase de demande de confirmation
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def is_expired(self, now: float | None = None) -> bool:
        return (now or time.time()) >= self.expires_at


@dataclass
class ConversationSession:
    """Mémoire courte pour conversation Jarvis ↔ Denis."""

    user_id: str = "denis"
    history: list[dict[str, str]] = field(default_factory=list)
    last_turn_ts: float = field(default_factory=time.time)
    pending: PendingBatch | None = None

    def is_expired(self, now: float | None = None) -> bool:
        now = now or time.time()
        return (now - self.last_turn_ts) > SESSION_TTL_SECONDS

    def reset(self) -> None:
        self.history = []
        self.last_turn_ts = time.time()
        self.pending = None

    # ----- gestion du batch en attente de confirmation -----

    def set_pending(
        self,
        routed_commands: list[Any],
        sensitivity_max: str,
        speak_question: str,
        now: float | None = None,
    ) -> None:
        ts = now or time.time()
        self.pending = PendingBatch(
            routed_commands=routed_commands,
            sensitivity_max=sensitivity_max,
            speak_question=speak_question,
            created_at=ts,
            expires_at=ts + PENDING_TTL_SECONDS,
        )

    def clear_pending(self) -> None:
        self.pending = None

    def get_pending(self, now: float | None = None) -> PendingBatch | None:
        if self.pending is None:
            return None
        if self.pending.is_expired(now):
            self.pending = None
            return None
        return self.pending

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
