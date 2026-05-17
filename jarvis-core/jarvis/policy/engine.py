"""
Policy engine — décide si une intention peut être exécutée.

Règles :
- Classifie l'intention en safe / sensible / critique (selon le device)
- Élève la sensibilité selon le contexte (heure, répétition, confiance)
- Renvoie une PolicyDecision structurée (jamais juste allow/deny)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from jarvis.domain.types import (
    ConversationContext,
    ConversationState,
    Intent,
    PolicyDecision,
    PolicyStatus,
    SensitivityLevel,
)


# Mapping device_name → sensibilité de base
# (chargé depuis settings.yaml dans la version finale, en dur ici pour démarrer)
DEFAULT_SENSITIVITY: dict[str, SensitivityLevel] = {
    "portail": SensitivityLevel.sensible,
    "porte_garage": SensitivityLevel.sensible,
    "alarme_zone_1": SensitivityLevel.critique,
    "alarme_zone_2": SensitivityLevel.critique,
}


class PolicyEngine:
    def __init__(
        self,
        device_sensitivity: Mapping[str, SensitivityLevel] | None = None,
        night_start_hour: int = 22,
        night_end_hour: int = 7,
        confidence_threshold: float = 0.7,
        repeat_window_seconds: int = 60,
        max_pin_attempts: int = 3,
        lock_duration_minutes: int = 60,
    ):
        self.device_sensitivity = dict(device_sensitivity or DEFAULT_SENSITIVITY)
        self.night_start = night_start_hour
        self.night_end = night_end_hour
        self.confidence_threshold = confidence_threshold
        self.repeat_window = timedelta(seconds=repeat_window_seconds)
        self.max_pin_attempts = max_pin_attempts
        self.lock_duration = timedelta(minutes=lock_duration_minutes)

    def _base_sensitivity(self, intent: Intent) -> SensitivityLevel:
        if intent.target and intent.target in self.device_sensitivity:
            return self.device_sensitivity[intent.target]
        # Par défaut : safe pour son/TV/mails, sensible pour scènes
        if intent.name in ("bonjour", "je_pars", "bonne_nuit"):
            return SensitivityLevel.sensible
        return SensitivityLevel.safe

    def _is_night(self, now: datetime) -> bool:
        h = now.hour
        if self.night_start > self.night_end:
            return h >= self.night_start or h < self.night_end
        return self.night_start <= h < self.night_end

    def _elevate(self, base: SensitivityLevel) -> SensitivityLevel:
        order = [SensitivityLevel.safe, SensitivityLevel.sensible, SensitivityLevel.critique]
        idx = order.index(base)
        return order[min(idx + 1, len(order) - 1)]

    def evaluate(
        self,
        intent: Intent,
        context: ConversationContext,
        now: datetime,
    ) -> PolicyDecision:
        # 0. Système verrouillé ?
        if context.is_locked(now):
            return PolicyDecision(
                status=PolicyStatus.locked,
                effective_sensitivity=SensitivityLevel.critique,
                reason=f"Système verrouillé jusqu'à {context.locked_until.isoformat()}",
            )

        base = self._base_sensitivity(intent)
        effective = base
        elevated = False
        reasons: list[str] = []

        # 1. Heure nocturne → +1 niveau
        if self._is_night(now):
            new_level = self._elevate(effective)
            if new_level != effective:
                elevated = True
                reasons.append(f"heure nocturne ({now.hour}h)")
                effective = new_level

        # 2. Confiance Claude basse → +1 niveau
        if intent.confidence < self.confidence_threshold:
            new_level = self._elevate(effective)
            if new_level != effective:
                elevated = True
                reasons.append(f"confiance basse ({intent.confidence:.2f})")
                effective = new_level

        # 3. Répétition récente → re-confirm
        if (
            context.last_command_ts
            and intent.name in context.recent_commands[-3:]
            and (now - context.last_command_ts) < self.repeat_window
        ):
            reasons.append("commande répétée récemment")
            new_level = self._elevate(effective)
            if new_level != effective:
                elevated = True
                effective = new_level

        # 4. Décision finale selon sensibilité effective
        if effective == SensitivityLevel.safe:
            status = PolicyStatus.allow
        elif effective == SensitivityLevel.sensible:
            status = PolicyStatus.require_confirmation
        else:  # critique
            status = PolicyStatus.require_pin

        reason = (
            f"base={base.value}, effective={effective.value}"
            + (f" — élevée par : {', '.join(reasons)}" if reasons else "")
        )

        return PolicyDecision(
            status=status,
            effective_sensitivity=effective,
            reason=reason,
            expires_at=now + timedelta(seconds=15) if status != PolicyStatus.allow else None,
            audit_required=True,
            elevation_applied=elevated,
        )
