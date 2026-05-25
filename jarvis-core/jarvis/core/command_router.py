"""CommandRouter — point d'entrée unique du backend Jarvis.

Pipeline complet d'une commande vocale :
    texte transcrit (Whisper)
    ↓
    LLMOrchestrator.plan_in_conversation()  (Claude Haiku 4.5 via OpenRouter)
    ↓
    ToolRouter.route_batch()  (validation schémas + budgets + rejet hallucination)
    ↓
    pour chaque RoutedCommand :
      Audit: command_requested
      ↓
      SubAgent.execute()  (mock ou handler réel selon ExecutionMode)
      ↓
      Audit: command_dispatched + command_succeeded/failed
    ↓
    ConversationSession mise à jour (mémoire 6 tours)
    ↓
    CommandRouterResult avec speak + executions
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jarvis.audit.store import SqliteAuditStore as AuditStore
from jarvis.domain.types import (
    AuditEvent,
    AuditEventType,
    ExecutionMode,
    ExecutionResult,
    ExecutionStatus,
    SensitivityLevel,
)
from jarvis.orchestrator.llm_client import LLMOrchestrator, LLMUnavailable, PlanResult
from jarvis.orchestrator.registry import SubAgentRegistry
from jarvis.orchestrator.session import ConversationSession, PendingBatch
from jarvis.orchestrator.tool_router import RoutedCommand, ToolRouter, ToolRouterRejection


# ----------------------------------------------------------------------
# Helpers confirmation orale (PRD §9.4)
# ----------------------------------------------------------------------

_YES_WORDS = {"oui", "ouais", "ok", "okay", "confirme", "confirmé", "confirmez",
              "vas-y", "go", "allez", "allez-y", "d'accord", "daccord", "yes"}
_NO_WORDS = {"non", "annule", "annulez", "annuler", "stop", "n'importe", "laisse",
              "laissez", "cancel", "no"}


def _normalize_yes_no(text: str) -> str:
    """Détecte si le texte est une réponse de confirmation oui/non/ambigu."""
    t = text.lower().strip().rstrip("!?.,;").strip()
    tokens = {w.strip(".,!?;:") for w in t.split()}
    is_yes = any(w in _YES_WORDS for w in tokens) or t in _YES_WORDS
    is_no = any(w in _NO_WORDS for w in tokens) or t in _NO_WORDS
    if is_yes and not is_no:
        return "yes"
    if is_no and not is_yes:
        return "no"
    return "ambiguous"


def _verb_for_tool(tool_name: str) -> str:
    """Verbe naturel français pour la phrase de demande de confirmation."""
    mapping = {
        "open_gate": "ouvrir le portail",
        "close_gate": "fermer le portail",
        "open_garage": "ouvrir la porte du garage",
        "close_garage": "fermer la porte du garage",
        "close_all_shutters": "fermer tous les volets",
        "open_all_shutters": "ouvrir tous les volets",
        "open_awning": "déployer le store banne",
        "arm_alarm": "activer l'alarme",
        "disarm_alarm": "désactiver l'alarme",
        "create_event": "créer ce rendez-vous dans votre agenda",
    }
    return mapping.get(tool_name, tool_name.replace("_", " "))


def _build_confirmation_speak(routed: list[RoutedCommand]) -> str:
    """Construit la phrase majordome de demande de confirmation pour un batch."""
    sensible_only = [r for r in routed if r.default_sensitivity == SensitivityLevel.sensible]
    critique = [r for r in routed if r.default_sensitivity == SensitivityLevel.critique]

    primary = critique[0] if critique else sensible_only[0] if sensible_only else routed[0]
    verb = _verb_for_tool(primary.tool_name)

    if critique:
        return (
            f"Cette action requiert votre confirmation, Monsieur. "
            f"Souhaitez-vous bien {verb} ?"
        )
    if len(routed) > 1:
        return f"Vous souhaitez bien {verb} (et les actions liées), Monsieur ?"
    return f"Vous souhaitez bien {verb}, Monsieur ?"


@dataclass
class CommandExecutionRecord:
    """Un tool_call exécuté (ou rejeté) avec son résultat."""

    domain: str
    tool_name: str
    correlation_id: str
    status: str           # "executed" | "rejected" | "failed"
    duration_ms: int = 0
    error: str | None = None
    response: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandRouterResult:
    """Résultat d'un tour de conversation Jarvis ↔ Denis."""

    speak: str                                   # phrase à faire prononcer par TTS
    executions: list[CommandExecutionRecord] = field(default_factory=list)
    llm_latency_ms: int = 0
    llm_model: str = ""
    llm_provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    rejection_reason: str | None = None          # Si tout le batch a été rejeté


class CommandRouter:
    """Point d'entrée unique : reçoit un texte transcrit, retourne speak + actions."""

    def __init__(
        self,
        registry: SubAgentRegistry,
        llm: LLMOrchestrator,
        tool_router: ToolRouter,
        audit: AuditStore,
        session: ConversationSession | None = None,
        mode: ExecutionMode = ExecutionMode.mock,
    ) -> None:
        self._registry = registry
        self._llm = llm
        self._tool_router = tool_router
        self._audit = audit
        self._session = session or ConversationSession()
        self._mode = mode

    @property
    def session(self) -> ConversationSession:
        return self._session

    async def handle_text(
        self,
        transcribed_text: str,
        now: datetime | None = None,
    ) -> CommandRouterResult:
        """Pipeline complet bout-en-bout avec confirmation orale PRD §9.4."""
        now = now or datetime.utcnow()

        # 0. Si une confirmation est en attente : intercepter avant tout LLM
        pending = self._session.get_pending()
        if pending is not None:
            return await self._handle_pending_response(pending, transcribed_text, now)

        # 1. Appel LLM (Claude Haiku 4.5 via OpenRouter par défaut)
        try:
            plan = self._llm.plan_in_conversation(
                self._session.as_llm_history(),
                transcribed_text,
            )
        except LLMUnavailable as e:
            self._session.add_user(transcribed_text)
            speak = "Je crains que mon entendement ne soit momentanément indisponible, Monsieur."
            self._session.add_assistant(speak)
            return CommandRouterResult(
                speak=speak,
                rejection_reason=f"llm_unavailable: {e}",
            )

        # 2. Routage tool_calls -> RoutedCommand (validation + budgets)
        executions: list[CommandExecutionRecord] = []
        rejection_reason: str | None = None
        routed: list[RoutedCommand] = []

        if plan.invocations:
            try:
                routed = self._tool_router.route_batch(plan.invocations)
            except ToolRouterRejection as e:
                rejection_reason = str(e)
                self._audit_event(
                    AuditEventType.command_failed,
                    correlation_id=str(uuid.uuid4()),
                    payload={
                        "stage": "tool_router_rejection",
                        "reason": rejection_reason,
                        "invocations": [
                            {"domain": inv.domain, "tool": inv.tool_name}
                            for inv in plan.invocations
                        ],
                    },
                    now=now,
                )

        # 3. Si le batch contient une action sensible/critique : STOP, demander confirmation
        sensitive_levels = {
            r.default_sensitivity for r in routed
            if r.default_sensitivity in (SensitivityLevel.sensible, SensitivityLevel.critique)
        }
        if routed and sensitive_levels:
            sensitivity_max = (
                SensitivityLevel.critique.value
                if SensitivityLevel.critique in sensitive_levels
                else SensitivityLevel.sensible.value
            )
            question = _build_confirmation_speak(routed)
            self._session.set_pending(
                routed_commands=routed,
                sensitivity_max=sensitivity_max,
                speak_question=question,
            )
            self._session.add_user(transcribed_text)
            self._session.add_assistant(question, [
                f"{r.domain}/{r.tool_name}" for r in routed
            ])
            for r in routed:
                self._audit_event(
                    AuditEventType.confirmation_requested,
                    correlation_id=r.command.correlation_id or str(uuid.uuid4()),
                    payload={
                        "domain": r.domain,
                        "tool": r.tool_name,
                        "sensitivity": r.default_sensitivity.value,
                    },
                    now=now,
                )
            return CommandRouterResult(
                speak=question,
                executions=[],
                llm_latency_ms=plan.latency_ms,
                llm_model=plan.model_used,
                llm_provider=plan.provider_used,
                input_tokens=plan.input_tokens,
                output_tokens=plan.output_tokens,
                stop_reason=plan.stop_reason,
                rejection_reason=rejection_reason,
            )

        # 4. Batch 100% safe — exécution directe
        for routed_cmd in routed:
            record = await self._execute_one(routed_cmd, now)
            executions.append(record)

        # 5. Met à jour la session
        self._session.add_user(transcribed_text)
        tool_summary = [f"{r.domain}/{r.tool_name}" for r in routed]
        self._session.add_assistant(plan.spoken_response, tool_summary)

        # 6. Construit le résultat
        # Si une recherche web a rapporté une réponse, c'est ELLE que Jarvis prononce
        # (le LLM planificateur ne connaît pas l'info récente, seul l'outil la ramène).
        search_answer = next(
            (
                e.response.get("answer")
                for e in executions
                if e.domain == "search" and e.response.get("answer")
            ),
            None,
        )
        speak = search_answer or plan.spoken_response or self._fallback_speak(rejection_reason)
        return CommandRouterResult(
            speak=speak,
            executions=executions,
            llm_latency_ms=plan.latency_ms,
            llm_model=plan.model_used,
            llm_provider=plan.provider_used,
            input_tokens=plan.input_tokens,
            output_tokens=plan.output_tokens,
            stop_reason=plan.stop_reason,
            rejection_reason=rejection_reason,
        )

    # ------------------------------------------------------------------
    # Gestion d'une réponse user à une confirmation déjà demandée
    # ------------------------------------------------------------------

    async def _handle_pending_response(
        self,
        pending: PendingBatch,
        transcribed_text: str,
        now: datetime,
    ) -> CommandRouterResult:
        answer = _normalize_yes_no(transcribed_text)

        if answer == "no":
            self._session.clear_pending()
            self._session.add_user(transcribed_text)
            speak = "Comme il vous plaira, Monsieur. J'annule."
            self._session.add_assistant(speak)
            for r in pending.routed_commands:
                self._audit_event(
                    AuditEventType.confirmation_refused,
                    correlation_id=r.command.correlation_id or str(uuid.uuid4()),
                    payload={"domain": r.domain, "tool": r.tool_name},
                    now=now,
                )
            return CommandRouterResult(speak=speak)

        if answer == "ambiguous":
            # On garde la confirmation active, on redemande
            speak = (
                "Je n'ai pas bien compris Monsieur. Souhaitez-vous que je procède ? "
                "Dites « oui » ou « non »."
            )
            self._session.add_user(transcribed_text)
            self._session.add_assistant(speak)
            return CommandRouterResult(speak=speak)

        # answer == "yes" — on exécute le batch confirmé
        executions: list[CommandExecutionRecord] = []
        for routed_cmd in pending.routed_commands:
            self._audit_event(
                AuditEventType.confirmation_accepted,
                correlation_id=routed_cmd.command.correlation_id or str(uuid.uuid4()),
                payload={"domain": routed_cmd.domain, "tool": routed_cmd.tool_name},
                now=now,
            )
            record = await self._execute_one(routed_cmd, now)
            executions.append(record)

        self._session.clear_pending()
        self._session.add_user(transcribed_text)
        speak = "Bien Monsieur, ce sera fait."
        self._session.add_assistant(speak, [
            f"{r.domain}/{r.tool_name}" for r in pending.routed_commands
        ])
        return CommandRouterResult(speak=speak, executions=executions)

    async def _execute_one(
        self,
        routed: RoutedCommand,
        now: datetime,
    ) -> CommandExecutionRecord:
        correlation_id = routed.command.correlation_id or str(uuid.uuid4())

        # Audit : command_requested + command_dispatched
        self._audit_event(
            AuditEventType.command_requested,
            correlation_id=correlation_id,
            payload={
                "domain": routed.domain,
                "tool": routed.tool_name,
                "action": routed.command.action.value,
                "device_url": routed.command.device_url,
                "default_sensitivity": routed.default_sensitivity.value,
            },
            now=now,
        )
        self._audit_event(
            AuditEventType.command_dispatched,
            correlation_id=correlation_id,
            payload={"domain": routed.domain, "tool": routed.tool_name},
            now=now,
        )

        # Exécution
        try:
            agent = self._registry.get_agent(routed.domain)
            result: ExecutionResult = await agent.execute(routed.command)
        except Exception as e:
            self._audit_event(
                AuditEventType.command_failed,
                correlation_id=correlation_id,
                payload={
                    "domain": routed.domain,
                    "tool": routed.tool_name,
                    "error": f"{type(e).__name__}: {e}",
                },
                now=now,
            )
            return CommandExecutionRecord(
                domain=routed.domain,
                tool_name=routed.tool_name,
                correlation_id=correlation_id,
                status="failed",
                error=f"{type(e).__name__}: {e}",
            )

        # Audit : command_succeeded / command_failed
        event_type = (
            AuditEventType.command_succeeded
            if result.status == ExecutionStatus.success
            else AuditEventType.command_failed
        )
        self._audit_event(
            event_type,
            correlation_id=correlation_id,
            payload={
                "domain": routed.domain,
                "tool": routed.tool_name,
                "duration_ms": result.duration_ms,
                "status": result.status.value,
            },
            now=now,
        )

        return CommandExecutionRecord(
            domain=routed.domain,
            tool_name=routed.tool_name,
            correlation_id=correlation_id,
            status="executed" if result.status == ExecutionStatus.success else "failed",
            duration_ms=result.duration_ms,
            error=result.error,
            response=dict(result.response) if result.response else {},
        )

    def _audit_event(
        self,
        event_type: AuditEventType,
        correlation_id: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        try:
            self._audit.append(
                AuditEvent(
                    ts=now,
                    correlation_id=correlation_id,
                    event_type=event_type,
                    user_id=self._session.user_id,
                    mode=self._mode,
                    payload=payload,
                )
            )
        except Exception:
            # L'audit ne doit jamais casser le pipeline (best-effort).
            pass

    @staticmethod
    def _fallback_speak(rejection_reason: str | None) -> str:
        if rejection_reason and "hallucination" in rejection_reason.lower():
            return "Je crains de ne pas pouvoir interpréter cette demande, Monsieur."
        if rejection_reason and "budget" in rejection_reason.lower():
            return "Je préfère traiter ces requêtes une à une, Monsieur. Par laquelle commencer ?"
        return "Bien Monsieur."
