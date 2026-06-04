"""Tests RBAC (PRD §30) — contrôle d'accès par rôle.

Couvre : capacités par défaut, rôle inconnu restrictif, admin intouchable,
élévation en direct + reset, et surtout le comportement du pipeline
``CommandRouter`` (refus visiteur/locataire, admin non bloqué, exécution
quand autorisé, élévation qui débloque le visiteur).

Exécutable avec pytest OU directement :
    .venv\\Scripts\\python.exe tests\\test_rbac.py
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from jarvis.core.command_router import CommandRouter
from jarvis.domain.types import (
    CommandAction,
    ExecutionResult,
    ExecutionStatus,
    SensitivityLevel,
)
from jarvis.orchestrator.session import ConversationSession
from jarvis.policy.roles import (
    ADMIN,
    LOCATAIRE,
    VISITEUR,
    RolePolicy,
    refusal_line,
    welcome_speech,
)


# ----------------------------------------------------------------------
# RolePolicy — unitaires
# ----------------------------------------------------------------------

def test_default_capabilities():
    p = RolePolicy()
    assert p.is_allowed(ADMIN, SensitivityLevel.critique)
    assert p.is_allowed(ADMIN, SensitivityLevel.safe)
    assert p.is_allowed(LOCATAIRE, SensitivityLevel.safe)
    assert not p.is_allowed(LOCATAIRE, SensitivityLevel.sensible)
    assert not p.is_allowed(VISITEUR, SensitivityLevel.safe)
    assert p.allowed_levels(VISITEUR) == set()


def test_unknown_role_is_restrictive():
    p = RolePolicy()
    assert p.normalize_role("bidon") == VISITEUR
    assert p.normalize_role(None) == VISITEUR
    assert not p.is_allowed("bidon", SensitivityLevel.safe)


def test_admin_is_untouchable():
    p = RolePolicy()
    p.set_level(ADMIN, "critique", False)  # tentative de dégrader l'admin
    assert p.is_allowed(ADMIN, SensitivityLevel.critique)  # ignoré


def test_live_elevation_and_reset():
    p = RolePolicy()
    p.set_level(VISITEUR, "safe", True)
    assert p.is_allowed(VISITEUR, SensitivityLevel.safe)
    p.reset()
    assert not p.is_allowed(VISITEUR, SensitivityLevel.safe)


def test_snapshot_shape():
    p = RolePolicy()
    snap = p.snapshot()
    assert snap[VISITEUR] == {"converse": True, "safe": False, "sensible": False, "critique": False}
    assert snap[ADMIN]["critique"] is True


def test_texts_use_placeholder_and_mention_visio():
    line = refusal_line(VISITEUR)
    assert "Monsieur" in line          # placeholder converti par _apply_title
    assert "visio" in line.lower()     # oriente vers la démo live avec Denis
    assert welcome_speech(VISITEUR)    # discours non vide


# ----------------------------------------------------------------------
# Échafaudage léger pour le pipeline
# ----------------------------------------------------------------------

class _FakePlan:
    def __init__(self, has_invocations: bool, spoken: str = "Bien."):
        self.invocations = [object()] if has_invocations else []
        self.spoken_response = spoken
        self.latency_ms = 1
        self.model_used = "fake"
        self.provider_used = "fake"
        self.input_tokens = 0
        self.output_tokens = 0
        self.stop_reason = "end"


class _FakeLLM:
    def __init__(self, plan): self._plan = plan
    def plan_in_conversation(self, history, text, role=None): return self._plan


class _FakeToolRouter:
    def __init__(self, routed): self._routed = routed
    def route_batch(self, invocations): return self._routed


class _FakeAudit:
    def append(self, event): pass


class _FakeAgent:
    async def execute(self, command):
        return ExecutionResult(
            status=ExecutionStatus.success,
            correlation_id=command.correlation_id,
            device_url=command.device_url,
            action=command.action,
            duration_ms=5,
            response={},
        )


class _FakeRegistry:
    def get_agent(self, domain): return _FakeAgent()


def _routed(domain, tool, sensitivity, action=CommandAction.on):
    cmd = SimpleNamespace(correlation_id="cid-1", action=action, device_url="dev://x")
    return SimpleNamespace(
        domain=domain, tool_name=tool, default_sensitivity=sensitivity, command=cmd
    )


def _router(routed, role_policy=None):
    return CommandRouter(
        registry=_FakeRegistry(),
        llm=_FakeLLM(_FakePlan(has_invocations=bool(routed))),
        tool_router=_FakeToolRouter(routed),
        audit=_FakeAudit(),
        session=ConversationSession(),
        role_policy=role_policy or RolePolicy(),
    )


# ----------------------------------------------------------------------
# Pipeline — comportement de sécurité
# ----------------------------------------------------------------------

def test_visiteur_safe_action_refused():
    r = _router([_routed("son", "set_volume", SensitivityLevel.safe)])
    res = asyncio.run(r.handle_text("monte le son", role=VISITEUR))
    assert res.executions == []
    assert "access_denied" in (res.rejection_reason or "")
    assert "visio" in res.speak.lower()


def test_locataire_sensible_action_refused():
    r = _router([_routed("portail", "open_gate", SensitivityLevel.sensible)])
    res = asyncio.run(r.handle_text("ouvre le portail", role=LOCATAIRE))
    assert res.executions == []
    assert "access_denied" in (res.rejection_reason or "")


def test_admin_sensible_not_denied_but_confirmed():
    r = _router([_routed("portail", "open_gate", SensitivityLevel.sensible)])
    res = asyncio.run(r.handle_text("ouvre le portail", role=ADMIN))
    assert res.executions == []
    assert "access_denied" not in (res.rejection_reason or "")
    assert r.session.get_pending() is not None  # demande de confirmation, pas un refus


def test_locataire_safe_action_executes():
    r = _router([_routed("son", "set_volume", SensitivityLevel.safe)])
    res = asyncio.run(r.handle_text("monte le son", role=LOCATAIRE))
    assert len(res.executions) == 1
    assert res.executions[0].status == "executed"


def test_live_elevation_lets_visiteur_through():
    policy = RolePolicy()
    policy.set_level(VISITEUR, "safe", True)  # élévation en direct
    r = _router([_routed("son", "set_volume", SensitivityLevel.safe)], role_policy=policy)
    res = asyncio.run(r.handle_text("monte le son", role=VISITEUR))
    assert len(res.executions) == 1
    assert res.executions[0].status == "executed"


def test_pending_confirmed_by_unauthorized_role_is_blocked():
    # Faille review HIGH : un pending sensible créé par l'admin ne doit PAS pouvoir
    # être validé par « oui » d'un rôle non autorisé (jury) sur la session partagée.
    r = _router([_routed("portail", "open_gate", SensitivityLevel.sensible)])
    res1 = asyncio.run(r.handle_text("ouvre le portail", role=ADMIN))
    assert res1.executions == []
    assert r.session.get_pending() is not None  # confirmation en attente
    res2 = asyncio.run(r.handle_text("oui", role=VISITEUR))  # le jury tente de valider
    assert res2.executions == []
    assert "access_denied" in (res2.rejection_reason or "")
    assert r.session.get_pending() is None  # pending purgé, action NON exécutée


def test_pending_confirmed_by_admin_executes():
    # Pas de régression : l'admin valide bien son propre pending.
    r = _router([_routed("portail", "open_gate", SensitivityLevel.sensible)])
    asyncio.run(r.handle_text("ouvre le portail", role=ADMIN))
    res = asyncio.run(r.handle_text("oui", role=ADMIN))
    assert len(res.executions) == 1
    assert res.executions[0].status == "executed"


# ----------------------------------------------------------------------
# Lanceur autonome (si pytest absent)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} tests OK")
    raise SystemExit(1 if failed else 0)
