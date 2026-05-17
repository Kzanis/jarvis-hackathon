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
)
from jarvis.orchestrator.llm_client import LLMOrchestrator, LLMUnavailable, PlanResult
from jarvis.orchestrator.registry import SubAgentRegistry
from jarvis.orchestrator.session import ConversationSession
from jarvis.orchestrator.tool_router import RoutedCommand, ToolRouter, ToolRouterRejection


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
        """Pipeline complet bout-en-bout."""
        now = now or datetime.utcnow()

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
                # Audit log de la hallucination/rejet
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

        # 3. Exécution des RoutedCommand
        for routed_cmd in routed:
            record = await self._execute_one(routed_cmd, now)
            executions.append(record)

        # 4. Met à jour la session
        self._session.add_user(transcribed_text)
        tool_summary = [f"{r.domain}/{r.tool_name}" for r in routed]
        self._session.add_assistant(plan.spoken_response, tool_summary)

        # 5. Construit le résultat
        speak = plan.spoken_response or self._fallback_speak(rejection_reason)
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
