"""
Protocoles (interfaces) pour les handlers et stores.
Permet de substituer mocks et implémentations réelles sans toucher au reste.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from jarvis.domain.types import (
    AuditEvent,
    ConversationContext,
    DeviceCommand,
    ExecutionResult,
)


@runtime_checkable
class DeviceHandler(Protocol):
    """Tout handler de devices (TaHoma, Freebox, etc.) doit implémenter ça."""

    name: str  # "tahoma", "freebox", ...

    async def list_devices(self) -> list[dict[str, Any]]:
        """Liste les devices contrôlables par ce handler."""
        ...

    async def execute(self, command: DeviceCommand) -> ExecutionResult:
        """Exécute une commande déjà validée par la policy."""
        ...

    async def health_check(self) -> bool:
        """Vérifie la connectivité du handler."""
        ...


@runtime_checkable
class AuditStore(Protocol):
    """Store d'audit. Append-only, signé HMAC, requêtable."""

    async def append(self, event: AuditEvent) -> str:
        """Append un événement, retourne sa signature."""
        ...

    async def recent(self, limit: int = 100) -> list[AuditEvent]:
        """Les N derniers événements."""
        ...

    async def verify_chain(self) -> bool:
        """Vérifie l'intégrité de la chaîne de signatures."""
        ...


@runtime_checkable
class ContextStore(Protocol):
    """Store des contextes conversationnels par utilisateur."""

    async def get(self, user_id: str) -> ConversationContext:
        ...

    async def save(self, ctx: ConversationContext) -> None:
        ...
