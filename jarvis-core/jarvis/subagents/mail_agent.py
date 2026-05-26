"""Sous-agent Mail : lecture de la messagerie (IMAP Gmail).

Lecture seule pour l'instant : résumé des non-lus, derniers messages. Les
réponses contiennent un champ `answer` (phrase orale) prononcé par Jarvis.
Réel si EXECUTION_MODE=production + MAIL_APP_PASSWORD défini, sinon simulé.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Protocol

from jarvis.domain.types import (
    CommandAction,
    DeviceCommand,
    ExecutionResult,
    SensitivityLevel,
)
from jarvis.subagents.base import ToolInvocation, ToolSpec


DOMAIN = "mail"


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="check_mail",
        description=(
            "Résume les e-mails NON LUS de la boîte de réception (combien, et de qui / "
            "quel objet). Pour 'ai-je des mails ?', 'des nouveaux messages ?', 'mes mails non lus'."
        ),
        params_schema={"type": "object", "additionalProperties": False, "properties": {}},
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
    ToolSpec(
        name="recent_mails",
        description=(
            "Liste les DERNIERS e-mails reçus (lus ou non), expéditeur + objet. "
            "Pour 'mes derniers mails', 'qu'est-ce que j'ai reçu'. 'count' = combien (défaut 5)."
        ),
        params_schema={
            "type": "object", "additionalProperties": False,
            "properties": {"count": {"type": "integer", "minimum": 1, "maximum": 10}},
        },
        default_sensitivity=SensitivityLevel.safe,
        domain=DOMAIN,
    ),
]

_TOOL_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOLS}


class _MailExecutor(Protocol):
    async def execute(self, command: DeviceCommand) -> ExecutionResult: ...


class MailAgent:
    """Sous-agent Mail (lecture IMAP)."""

    domain: str = DOMAIN
    tools: list[ToolSpec] = TOOLS

    def __init__(self, executor: _MailExecutor | None = None) -> None:
        self._executor = executor or self._build_default_executor()

    @staticmethod
    def _build_default_executor() -> _MailExecutor:
        # Le handler IMAP gère lui-même la simulation si non configuré.
        from jarvis.handlers.mail_imap import MailImapHandler
        return MailImapHandler()

    def resolve(self, invocation: ToolInvocation) -> DeviceCommand:
        if invocation.domain != DOMAIN:
            raise ValueError(f"MailAgent reçoit un mauvais domaine : {invocation.domain!r}")
        spec = _TOOL_BY_NAME.get(invocation.tool_name)
        if spec is None:
            raise ValueError(
                f"Tool inconnu pour {DOMAIN} : {invocation.tool_name!r}. "
                f"Disponibles : {sorted(_TOOL_BY_NAME)}"
            )
        args: dict[str, Any] = invocation.arguments or {}
        cid = args.get("__correlation_id") or str(uuid.uuid4())
        params: dict[str, Any] = {"intent": invocation.tool_name}
        if "count" in args:
            params["count"] = int(args["count"])
        return DeviceCommand(
            device_url=f"mail:{invocation.tool_name}",
            action=CommandAction.speak,
            params=params,
            correlation_id=cid,
        )

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        return await self._executor.execute(command)
