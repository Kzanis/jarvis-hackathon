"""
Types métier centraux de Jarvis. Stable, sans dépendance externe.
Réutilisable par tous les modules (policy, core, handlers, mocks, audit).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ============================================
# MODE D'EXÉCUTION
# ============================================

class ExecutionMode(str, Enum):
    """Mode d'exécution global. Mock par défaut (sécurité)."""
    mock = "mock"            # Simulateurs (jury, dev)
    replay = "replay"        # Rejoue une session enregistrée
    production = "production"  # Vrais devices (nécessite ALLOW_REAL_DEVICES=true)


# ============================================
# COMMANDES & INTENTS
# ============================================

class CommandAction(str, Enum):
    """Actions physiques disponibles."""
    open = "open"
    close = "close"
    stop = "stop"
    set_closure = "set_closure"
    on = "on"
    off = "off"
    arm = "arm"
    disarm = "disarm"
    set_volume = "set_volume"
    set_channel = "set_channel"
    speak = "speak"


class Intent(BaseModel):
    """Une intention extraite du langage naturel par Claude."""
    name: str                              # ex: "open_gate", "close_all_shutters"
    action: CommandAction
    target: Optional[str] = None           # nom logique du device ou groupe
    params: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0                # 0..1, score Claude
    raw_text: str = ""                     # texte transcrit Whisper
    user_id: str = "denis"                 # liste blanche, 1 user par défaut


class DeviceCommand(BaseModel):
    """Commande normalisée prête à être exécutée par un handler."""
    device_url: str                        # ID TaHoma ou autre
    action: CommandAction
    params: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str                    # lie tous les events d'une même commande


# ============================================
# SÉCURITÉ : SENSIBILITÉ & DÉCISION POLICY
# ============================================

class SensitivityLevel(str, Enum):
    """3 niveaux de sensibilité d'une commande."""
    safe = "safe"            # exécution directe (volume, chaîne, mails)
    sensible = "sensible"    # confirmation orale ("Confirmez Monsieur ?")
    critique = "critique"    # confirmation + PIN vocal 4 chiffres


class PolicyStatus(str, Enum):
    """Décision finale de la policy."""
    allow = "allow"                                # OK, exécute
    require_confirmation = "require_confirmation"  # passer en PendingConfirmation
    require_pin = "require_pin"                    # passer en PendingPin
    deny = "deny"                                  # rejet définitif
    locked = "locked"                              # système verrouillé (3 échecs PIN)


class PolicyDecision(BaseModel):
    """Réponse structurée du policy engine."""
    status: PolicyStatus
    effective_sensitivity: SensitivityLevel
    reason: str                                    # raison humaine, loggée
    expires_at: Optional[datetime] = None          # pour PendingConfirmation
    audit_required: bool = True
    elevation_applied: bool = False                # True si sensibilité auto-élevée


# ============================================
# ÉTAT CONVERSATIONNEL & CONFIRMATION
# ============================================

class ConversationState(str, Enum):
    """État courant de la conversation Jarvis ↔ Denis."""
    idle = "idle"
    pending_sensible = "pending_sensible"
    pending_critique = "pending_critique"
    locked = "locked"


class PendingConfirmation(BaseModel):
    """Une confirmation en attente."""
    intent: Intent
    state: ConversationState
    created_at: datetime
    expires_at: datetime
    pin_attempts: int = 0                          # pour state pending_critique
    correlation_id: str


class ConversationContext(BaseModel):
    """Contexte conversationnel d'un utilisateur. Persistant entre tours."""
    user_id: str = "denis"
    state: ConversationState = ConversationState.idle
    pending: Optional[PendingConfirmation] = None
    last_command_ts: Optional[datetime] = None
    recent_commands: list[str] = Field(default_factory=list)  # noms des 10 dernières
    locked_until: Optional[datetime] = None

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and now < self.locked_until


# ============================================
# RÉSULTAT D'EXÉCUTION
# ============================================

class ExecutionStatus(str, Enum):
    success = "success"
    failure = "failure"
    partial = "partial"


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    correlation_id: str
    device_url: str
    action: CommandAction
    duration_ms: int = 0
    error: Optional[str] = None
    response: dict[str, Any] = Field(default_factory=dict)


# ============================================
# AUDIT EVENTS
# ============================================

class AuditEventType(str, Enum):
    command_requested = "command_requested"
    policy_evaluated = "policy_evaluated"
    confirmation_requested = "confirmation_requested"
    confirmation_accepted = "confirmation_accepted"
    confirmation_refused = "confirmation_refused"
    confirmation_timeout = "confirmation_timeout"
    pin_attempted = "pin_attempted"
    pin_succeeded = "pin_succeeded"
    pin_failed = "pin_failed"
    command_dispatched = "command_dispatched"
    command_succeeded = "command_succeeded"
    command_failed = "command_failed"
    system_locked = "system_locked"
    rate_limited = "rate_limited"
    access_denied = "access_denied"  # commande refusée par le contrôle de rôle (RBAC, PRD §30)


class AuditEvent(BaseModel):
    """Un événement d'audit. Append-only, signé HMAC."""
    ts: datetime
    correlation_id: str
    event_type: AuditEventType
    user_id: str
    mode: ExecutionMode
    sensitivity: Optional[SensitivityLevel] = None
    command_name: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
