"""
Unit tests for LocalFallbackDecisionProvider.

These tests are pure synchronous-style async with no DB, no network,
and no mocking required.  The provider must always return a valid
RoutingDecision without raising.
"""

from __future__ import annotations

import dataclasses
import pytest

from app.decision.contracts import RequestState
from app.decision.fallback_provider import LocalFallbackDecisionProvider


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture
def provider() -> LocalFallbackDecisionProvider:
    return LocalFallbackDecisionProvider()


def make_state(**overrides) -> RequestState:
    """Base state with sensible defaults; override individual fields."""
    base = dict(
        token_count=200,
        has_code=False,
        has_vision=False,
        requires_reasoning=False,
        tool_call_type=None,
        retrieved_doc_count=0,
        query_complexity_score=0.2,
    )
    base.update(overrides)
    return RequestState(**base)


# ── Rule tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vision_routes_to_vision(provider):
    decision = await provider.route_request(make_state(has_vision=True))
    assert decision.model == "vision"
    assert decision.provider == "local_fallback"
    assert 0.0 < decision.confidence <= 1.0


@pytest.mark.asyncio
async def test_vision_takes_priority_over_code(provider):
    """Vision flag should win even if has_code is also True."""
    decision = await provider.route_request(
        make_state(has_vision=True, has_code=True)
    )
    assert decision.model == "vision"


@pytest.mark.asyncio
async def test_code_without_reasoning_routes_to_code(provider):
    decision = await provider.route_request(
        make_state(has_code=True, requires_reasoning=False)
    )
    assert decision.model == "code"


@pytest.mark.asyncio
async def test_code_with_reasoning_does_not_route_to_code(provider):
    """
    Code + reasoning should NOT go to the code model.
    Complex reasoning overrides the code specialisation heuristic.
    Expected: reasoning model (complexity default 0.2 is below threshold,
    but requires_reasoning=True is explicit).
    """
    decision = await provider.route_request(
        make_state(has_code=True, requires_reasoning=True)
    )
    assert decision.model == "reasoning"


@pytest.mark.asyncio
async def test_large_token_count_routes_to_large(provider):
    decision = await provider.route_request(make_state(token_count=9_000))
    assert decision.model == "large"


@pytest.mark.asyncio
async def test_reasoning_flag_routes_to_reasoning(provider):
    decision = await provider.route_request(make_state(requires_reasoning=True))
    assert decision.model == "reasoning"


@pytest.mark.asyncio
async def test_high_complexity_score_routes_to_reasoning(provider):
    decision = await provider.route_request(
        make_state(query_complexity_score=0.85)
    )
    assert decision.model == "reasoning"


@pytest.mark.asyncio
async def test_default_routes_to_small(provider):
    """All signals absent — should default to the small model."""
    decision = await provider.route_request(make_state())
    assert decision.model == "small"


@pytest.mark.asyncio
async def test_decision_always_has_required_fields(provider):
    """RoutingDecision must be structurally complete regardless of input."""
    for state in [
        make_state(),
        make_state(has_vision=True),
        make_state(token_count=100_000),
        make_state(query_complexity_score=0.99),
    ]:
        decision = await provider.route_request(state)
        assert decision.model
        assert decision.provider == "local_fallback"
        assert 0.0 <= decision.confidence <= 1.0
        # reason may be None per contract; fallback always provides one
        assert decision.reason is not None


@pytest.mark.asyncio
async def test_confidence_is_conservative(provider):
    """
    Fallback confidence values must be < 0.80 (below HIGH_CONFIDENCE_THRESHOLD).
    Fallback rules are heuristics — they should not claim high confidence.
    """
    for state in [make_state(), make_state(has_vision=True), make_state(has_code=True)]:
        decision = await provider.route_request(state)
        assert decision.confidence < 0.80, (
            f"Fallback confidence {decision.confidence} should be below 0.80 "
            f"for model={decision.model}"
        )
