"""
Unit tests for GroqDecisionProvider.

The GroqDecisionClient is injected and replaced with a mock so no real
Groq API calls are made.  These tests verify:
  - Correct translation of Groq JSON response → RoutingDecision
  - Validation of unexpected model values
  - DecisionProviderError raised on API failure or bad JSON
  - Confidence clamped to [0.0, 1.0]
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.decision.base import DecisionProviderError
from app.decision.contracts import RequestState
from app.decision.groq_provider import GroqDecisionProvider


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_state(**overrides) -> RequestState:
    base = dict(
        token_count=300,
        has_code=False,
        has_vision=False,
        requires_reasoning=False,
        tool_call_type=None,
        retrieved_doc_count=0,
        query_complexity_score=0.3,
    )
    base.update(overrides)
    return RequestState(**base)


def mock_groq_client(response: dict) -> MagicMock:
    """Return a mock GroqDecisionClient that resolves with `response`."""
    client = MagicMock()
    client.get_routing_decision = AsyncMock(return_value=response)
    return client


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_routes_to_code():
    client = mock_groq_client({"model": "code", "confidence": 0.88, "reason": "Has code"})
    provider = GroqDecisionProvider(client=client)
    decision = await provider.route_request(make_state(has_code=True))
    assert decision.model == "code"
    assert decision.confidence == pytest.approx(0.88)
    assert decision.provider == "groq"
    assert "code" in decision.reason.lower()


@pytest.mark.asyncio
async def test_routes_to_vision():
    client = mock_groq_client({"model": "vision", "confidence": 0.95, "reason": "Vision"})
    provider = GroqDecisionProvider(client=client)
    decision = await provider.route_request(make_state(has_vision=True))
    assert decision.model == "vision"


@pytest.mark.asyncio
async def test_routes_to_small_default():
    client = mock_groq_client({"model": "small", "confidence": 0.75, "reason": "Simple"})
    provider = GroqDecisionProvider(client=client)
    decision = await provider.route_request(make_state())
    assert decision.model == "small"
    assert decision.provider == "groq"


@pytest.mark.asyncio
async def test_all_valid_models_accepted():
    for model in ["small", "large", "code", "vision", "reasoning"]:
        client = mock_groq_client({"model": model, "confidence": 0.80, "reason": "test"})
        provider = GroqDecisionProvider(client=client)
        decision = await provider.route_request(make_state())
        assert decision.model == model


# ── Confidence clamping ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confidence_clamped_above_1():
    """Groq may occasionally return confidence > 1.0 — clamp to 1.0."""
    client = mock_groq_client({"model": "small", "confidence": 1.5, "reason": "test"})
    provider = GroqDecisionProvider(client=client)
    decision = await provider.route_request(make_state())
    assert decision.confidence <= 1.0


@pytest.mark.asyncio
async def test_confidence_clamped_below_0():
    client = mock_groq_client({"model": "small", "confidence": -0.2, "reason": "test"})
    provider = GroqDecisionProvider(client=client)
    decision = await provider.route_request(make_state())
    assert decision.confidence >= 0.0


# ── Error handling ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_raises_on_unexpected_model():
    client = mock_groq_client({"model": "turbo", "confidence": 0.9, "reason": "test"})
    provider = GroqDecisionProvider(client=client)
    with pytest.raises(DecisionProviderError, match="unexpected model"):
        await provider.route_request(make_state())


@pytest.mark.asyncio
async def test_raises_on_api_exception():
    client = MagicMock()
    client.get_routing_decision = AsyncMock(side_effect=Exception("Connection timeout"))
    provider = GroqDecisionProvider(client=client)
    with pytest.raises(DecisionProviderError, match="Groq provider failed"):
        await provider.route_request(make_state())


@pytest.mark.asyncio
async def test_raises_on_missing_confidence():
    client = mock_groq_client({"model": "small", "reason": "missing confidence"})
    provider = GroqDecisionProvider(client=client)
    with pytest.raises(DecisionProviderError, match="confidence"):
        await provider.route_request(make_state())


@pytest.mark.asyncio
async def test_reason_can_be_none():
    """reason field is optional in the Groq response."""
    client = mock_groq_client({"model": "large", "confidence": 0.7})
    provider = GroqDecisionProvider(client=client)
    decision = await provider.route_request(make_state())
    assert decision.model == "large"
    assert decision.reason is None
