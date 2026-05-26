"""5 tests golden path pour le sprint orchestrateur (19-22 mai).

Tous marqués xfail aujourd'hui (17/05) — ils doivent passer au plus tard ven 22/05 (J-13).
C'est le critère de "sprint orchestrateur terminé".

Lancer avec :
    cd jarvis-core && pytest tests/unit/test_orchestrator_golden_path.py -v
"""
from __future__ import annotations

import pytest

from jarvis.orchestrator.registry import (
    SubAgentRegistry,
    build_default_registry,
)
from jarvis.orchestrator.tool_router import ToolRouter, ToolRouterRejection
from jarvis.subagents.base import ToolInvocation


# ============================================================
# Test 1 — Registry construit sans erreur (tahoma/devialet/agenda + search + freebox)
# ============================================================
def test_registry_has_expected_subagents() -> None:
    """Le registre doit exposer les sous-agents domotique + recherche + télé."""
    registry = build_default_registry()
    assert set(registry.domains()) == {"tahoma", "devialet", "agenda", "search", "freebox"}


# ============================================================
# Test 2 — Hallucination LLM (domaine inconnu) rejetée
# ============================================================
def test_hallucinated_domain_is_rejected() -> None:
    """Un domaine fabriqué par le LLM doit être REJECT par le router."""
    registry = build_default_registry()
    router = ToolRouter(registry)
    fake = ToolInvocation(
        domain="cuisine_quantique",
        tool_name="cook_pasta",
        arguments={},
    )
    with pytest.raises(ToolRouterRejection) as exc:
        router.route_batch([fake])
    assert "cuisine_quantique" in str(exc.value).lower() or "hors registry" in str(exc.value).lower()


# ============================================================
# Test 3 — Hallucination LLM (tool inconnu dans domaine valide) rejetée
# ============================================================
def test_hallucinated_tool_is_rejected() -> None:
    """Un tool inventé dans un domaine valide doit être REJECT."""
    registry = build_default_registry()
    router = ToolRouter(registry)
    fake = ToolInvocation(
        domain="tahoma",
        tool_name="launch_nuclear_missile",  # n'existe pas
        arguments={},
    )
    with pytest.raises(ToolRouterRejection):
        router.route_batch([fake])


# ============================================================
# Test 4 — Composition multi-tool (mode cinéma) OK
# ============================================================
def test_cinema_mode_composes_three_tools() -> None:
    """"Mode cinéma" = close_shutter salon + set_source(tv) + set_volume(80)."""
    registry = build_default_registry()
    router = ToolRouter(registry)
    invocations = [
        ToolInvocation(
            domain="tahoma",
            tool_name="close_shutter",
            arguments={"shutter_name": "salon"},
        ),
        ToolInvocation(
            domain="devialet",
            tool_name="set_source",
            arguments={"zone": "salon", "source": "tv"},
        ),
        ToolInvocation(
            domain="devialet",
            tool_name="set_volume",
            arguments={"zone": "salon", "volume": 80},
        ),
    ]
    routed = router.route_batch(invocations)
    assert len(routed) == 3
    assert {r.domain for r in routed} == {"tahoma", "devialet"}


# ============================================================
# Test 5 — Budget critique respecté (max 1 critique par requête)
# ============================================================
def test_budget_critique_max_one_per_request() -> None:
    """Le LLM ne peut pas demander 2 actions critiques en une seule requête."""
    registry = build_default_registry()
    router = ToolRouter(registry)
    # disarm_alarm est niveau critique
    invocations = [
        ToolInvocation(domain="tahoma", tool_name="disarm_alarm", arguments={}),
        ToolInvocation(domain="tahoma", tool_name="disarm_alarm", arguments={}),
    ]
    with pytest.raises(ToolRouterRejection) as exc:
        router.route_batch(invocations)
    assert "budget" in str(exc.value).lower() or "critique" in str(exc.value).lower()


# ============================================================
# BONUS — Test 0 : sanity check imports (doit passer dès aujourd'hui)
# ============================================================
def test_orchestrator_imports_are_wired() -> None:
    """Vérifie que les imports cross-modules ne sont pas cassés.

    Doit passer DÈS LE 17/05 — c'est le seul test qui ne soit pas xfail.
    """
    assert SubAgentRegistry is not None
    assert ToolRouter is not None
    assert ToolInvocation is not None
    assert ToolRouterRejection is not None
