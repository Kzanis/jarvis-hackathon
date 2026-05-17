"""
Orchestrator — pipeline complet d'une commande Jarvis.

Flux :
    Intent
    ↓
    PolicyEngine.evaluate()
    ↓
    Audit: command_requested + policy_evaluated
    ↓
    Selon PolicyDecision :
      - allow         → execute immédiatement
      - require_confirmation → met en PendingConfirmation, attend "oui"
      - require_pin   → met en PendingCritique, attend PIN
      - deny / locked → refus
    ↓
    handler.execute() (uniquement après autorisation)
    ↓
    Audit: command_dispatched + command_succeeded/failed
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from jarvis.domain.protocols import AuditStore, DeviceHandler
from jarvis.domain.types import (
    AuditEvent,
    AuditEventType,
    ConversationContext,
    ConversationState,
    CommandAction,
    DeviceCommand,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    Intent,
    PendingConfirmation,
    PolicyDecision,
    PolicyStatus,
    SensitivityLevel,
)
from jarvis.policy.engine import PolicyEngine


class OrchestratorResult:
    """Résultat exposé à l'appelant (PWA, FastAPI, CLI test)."""
    def __init__(
        self,
        outcome: str,                 # "executed" | "awaiting_confirmation" | "awaiting_pin" | "denied" | "locked"
        speak: str,                   # phrase à dire par TTS
        decision: PolicyDecision,
        execution: Optional[ExecutionResult] = None,
        correlation_id: str = "",
    ):
        self.outcome = outcome
        self.speak = speak
        self.decision = decision
        self.execution = execution
        self.correlation_id = correlation_id


class Orchestrator:
    def __init__(
        self,
        policy: PolicyEngine,
        handler: DeviceHandler,
        audit: AuditStore,
        device_url_resolver: dict[str, str],  # nom_logique → url TaHoma
        mode: ExecutionMode = ExecutionMode.mock,
    ):
        self.policy = policy
        self.handler = handler
        self.audit = audit
        self.url_resolver = device_url_resolver
        self.mode = mode

    def _audit(
        self,
        event_type: AuditEventType,
        correlation_id: str,
        ctx: ConversationContext,
        intent: Optional[Intent] = None,
        sensitivity: Optional[SensitivityLevel] = None,
        payload: Optional[dict] = None,
    ) -> None:
        evt = AuditEvent(
            ts=datetime.utcnow(),
            correlation_id=correlation_id,
            event_type=event_type,
            user_id=ctx.user_id,
            mode=self.mode,
            sensitivity=sensitivity,
            command_name=intent.name if intent else None,
            payload=payload or {},
        )
        self.audit.append(evt)

    async def handle_intent(
        self,
        intent: Intent,
        context: ConversationContext,
        now: Optional[datetime] = None,
    ) -> OrchestratorResult:
        now = now or datetime.utcnow()
        correlation_id = str(uuid.uuid4())

        # 1. Audit demande
        self._audit(AuditEventType.command_requested, correlation_id, context, intent)

        # 2. Évalue policy
        decision = self.policy.evaluate(intent, context, now)
        self._audit(
            AuditEventType.policy_evaluated,
            correlation_id,
            context,
            intent,
            sensitivity=decision.effective_sensitivity,
            payload={"status": decision.status.value, "reason": decision.reason},
        )

        # 3. Branche selon décision
        if decision.status == PolicyStatus.locked:
            return OrchestratorResult(
                outcome="locked",
                speak="Je crains que le système ne soit verrouillé Monsieur. Veuillez patienter.",
                decision=decision,
                correlation_id=correlation_id,
            )

        if decision.status == PolicyStatus.deny:
            return OrchestratorResult(
                outcome="denied",
                speak="Je crains que cette action ne soit pas autorisée Monsieur.",
                decision=decision,
                correlation_id=correlation_id,
            )

        if decision.status == PolicyStatus.require_confirmation:
            context.state = ConversationState.pending_sensible
            context.pending = PendingConfirmation(
                intent=intent,
                state=ConversationState.pending_sensible,
                created_at=now,
                expires_at=decision.expires_at,
                correlation_id=correlation_id,
            )
            self._audit(
                AuditEventType.confirmation_requested,
                correlation_id,
                context,
                intent,
                sensitivity=decision.effective_sensitivity,
            )
            target_label = intent.target or intent.name
            return OrchestratorResult(
                outcome="awaiting_confirmation",
                speak=f"Vous souhaitez bien {self._verb_phrase(intent)} Monsieur ?",
                decision=decision,
                correlation_id=correlation_id,
            )

        if decision.status == PolicyStatus.require_pin:
            context.state = ConversationState.pending_critique
            context.pending = PendingConfirmation(
                intent=intent,
                state=ConversationState.pending_critique,
                created_at=now,
                expires_at=decision.expires_at,
                correlation_id=correlation_id,
            )
            self._audit(
                AuditEventType.confirmation_requested,
                correlation_id,
                context,
                intent,
                sensitivity=decision.effective_sensitivity,
                payload={"requires_pin": True},
            )
            return OrchestratorResult(
                outcome="awaiting_pin",
                speak="Cette action requiert votre code de sécurité Monsieur.",
                decision=decision,
                correlation_id=correlation_id,
            )

        # 4. status == allow → "speak first, execute after"
        # On répond TOUT DE SUITE par la voix (Bien Monsieur),
        # l'exécution part en arrière-plan via asyncio.create_task().
        # Gain UX : Denis entend Jarvis sous 200ms, le volet bouge en parallèle.
        speak_phrase = self._success_phrase(intent)
        asyncio.create_task(
            self._execute(intent, context, decision, correlation_id, now)
        )
        return OrchestratorResult(
            outcome="executed",
            speak=speak_phrase,
            decision=decision,
            correlation_id=correlation_id,
        )

    async def _execute(
        self,
        intent: Intent,
        context: ConversationContext,
        decision: PolicyDecision,
        correlation_id: str,
        now: datetime,
    ) -> OrchestratorResult:
        device_url = self.url_resolver.get(intent.target or "", intent.target or "")
        command = DeviceCommand(
            device_url=device_url,
            action=intent.action,
            params=intent.params,
            correlation_id=correlation_id,
        )

        self._audit(
            AuditEventType.command_dispatched,
            correlation_id,
            context,
            intent,
            sensitivity=decision.effective_sensitivity,
            payload={"device_url": device_url, "action": intent.action.value},
        )

        try:
            result = await self.handler.execute(command)
        except Exception as e:
            self._audit(
                AuditEventType.command_failed,
                correlation_id,
                context,
                intent,
                sensitivity=decision.effective_sensitivity,
                payload={"error": str(e)},
            )
            return OrchestratorResult(
                outcome="executed",
                speak=f"Je crains qu'une erreur ne soit survenue Monsieur. {type(e).__name__}",
                decision=decision,
                correlation_id=correlation_id,
            )

        if result.status == ExecutionStatus.success:
            self._audit(
                AuditEventType.command_succeeded,
                correlation_id,
                context,
                intent,
                sensitivity=decision.effective_sensitivity,
                payload={"duration_ms": result.duration_ms},
            )
            context.last_command_ts = now
            context.recent_commands.append(intent.name)
            if len(context.recent_commands) > 10:
                context.recent_commands.pop(0)
            context.state = ConversationState.idle
            context.pending = None
            return OrchestratorResult(
                outcome="executed",
                speak=self._success_phrase(intent),
                decision=decision,
                execution=result,
                correlation_id=correlation_id,
            )
        else:
            self._audit(
                AuditEventType.command_failed,
                correlation_id,
                context,
                intent,
                sensitivity=decision.effective_sensitivity,
                payload={"error": result.error or "unknown"},
            )
            return OrchestratorResult(
                outcome="executed",
                speak=f"L'action a échoué Monsieur. {result.error or ''}",
                decision=decision,
                execution=result,
                correlation_id=correlation_id,
            )

    def _verb_phrase(self, intent: Intent) -> str:
        verb_map = {
            CommandAction.open: "ouvrir",
            CommandAction.close: "fermer",
            CommandAction.stop: "arrêter",
            CommandAction.arm: "activer",
            CommandAction.disarm: "désactiver",
            CommandAction.on: "allumer",
            CommandAction.off: "éteindre",
        }
        verb = verb_map.get(intent.action, "exécuter")
        target = intent.target or "cette action"
        return f"{verb} {target.replace('_', ' ')}"

    def _success_phrase(self, intent: Intent) -> str:
        return "Bien Monsieur. Ce sera fait."

    # ============================================
    # Confirmation utilisateur (oui/non/pin)
    # ============================================

    async def confirm(
        self,
        context: ConversationContext,
        response: str,
        now: Optional[datetime] = None,
    ) -> OrchestratorResult:
        """Traite une réponse de confirmation (oui/non/timeout)."""
        now = now or datetime.utcnow()
        pending = context.pending

        if pending is None or context.state == ConversationState.idle:
            return OrchestratorResult(
                outcome="denied",
                speak="Je n'ai aucune action en attente de confirmation Monsieur.",
                decision=PolicyDecision(
                    status=PolicyStatus.deny,
                    effective_sensitivity=SensitivityLevel.safe,
                    reason="no_pending",
                ),
            )

        # Expiration ?
        if now > pending.expires_at:
            self._audit(
                AuditEventType.confirmation_timeout,
                pending.correlation_id,
                context,
                pending.intent,
            )
            context.state = ConversationState.idle
            context.pending = None
            return OrchestratorResult(
                outcome="denied",
                speak="Pas de confirmation reçue Monsieur, j'annule la demande.",
                decision=PolicyDecision(
                    status=PolicyStatus.deny,
                    effective_sensitivity=SensitivityLevel.safe,
                    reason="confirmation_timeout",
                ),
                correlation_id=pending.correlation_id,
            )

        # Détection yes/no (basique, à raffiner via Claude en prod)
        normalized = response.lower().strip()
        is_yes = any(w in normalized for w in ["oui", "confirmé", "vas-y", "go", "ok"])
        is_no = any(w in normalized for w in ["non", "annule", "stop", "n'importe"])

        if is_no:
            self._audit(
                AuditEventType.confirmation_refused,
                pending.correlation_id,
                context,
                pending.intent,
            )
            context.state = ConversationState.idle
            context.pending = None
            return OrchestratorResult(
                outcome="denied",
                speak="Bien Monsieur, j'annule.",
                decision=PolicyDecision(
                    status=PolicyStatus.deny,
                    effective_sensitivity=SensitivityLevel.safe,
                    reason="user_refused",
                ),
                correlation_id=pending.correlation_id,
            )

        if not is_yes:
            return OrchestratorResult(
                outcome="awaiting_confirmation",
                speak="Je n'ai pas bien compris Monsieur, dois-je continuer ?",
                decision=PolicyDecision(
                    status=PolicyStatus.require_confirmation,
                    effective_sensitivity=SensitivityLevel.sensible,
                    reason="ambiguous_response",
                    expires_at=pending.expires_at,
                ),
                correlation_id=pending.correlation_id,
            )

        # YES confirmé : on exécute
        self._audit(
            AuditEventType.confirmation_accepted,
            pending.correlation_id,
            context,
            pending.intent,
        )
        decision = PolicyDecision(
            status=PolicyStatus.allow,
            effective_sensitivity=SensitivityLevel.sensible,
            reason="user_confirmed",
        )
        return await self._execute(
            pending.intent, context, decision, pending.correlation_id, now
        )
