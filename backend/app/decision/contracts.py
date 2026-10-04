"""
JevGuard decision contracts.

These two dataclasses are the entire API surface of the decision layer.
No other module in JevGuard — routes, services, tests — ever imports a
provider-internal type (JevResponse, LocalResult, …).  Everything programs
against RequestState → RoutingDecision.

If Jev's wire format changes tomorrow, only jev_client.py and jev_provider.py
need updating.  Nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RequestState:
    """
    Compact, feature-engineered representation of a single request.

    All feature engineering MUST happen before calling any DecisionProvider.
    Never pass raw user text as a field here — derive meaningful scalar
    features first.  This keeps Jev inputs small (token efficiency) and
    keeps features consistent across both providers.

    Fields
    ------
    token_count
        Estimated token count of the full request context.
    has_code
        True if the request contains a code block or references code.
    has_vision
        True if the request includes an image or requires visual reasoning.
    requires_reasoning
        True if the request involves multi-step reasoning or complex logic.
    tool_call_type
        Category of tool being invoked, if any.
        "delete" | "write" | "read" | "execute" | None
    retrieved_doc_count
        Number of candidate documents retrieved (RAG phase).
        Zero until Phase 6.
    query_complexity_score
        Pre-computed complexity signal in [0.0, 1.0].
        Must be derived deterministically — never by calling an LLM.
    """

    token_count: int
    has_code: bool
    has_vision: bool
    requires_reasoning: bool
    tool_call_type: Optional[str]
    retrieved_doc_count: int
    query_complexity_score: float


@dataclass
class RoutingDecision:
    """
    The object the rest of JevGuard receives from the decision layer.

    Fields
    ------
    model
        Logical model category to route to.
        Values: "small" | "large" | "code" | "vision" | "reasoning"
        Resolved to a concrete model identifier in Phase 4
        via configs/model_routing.yaml.
    confidence
        Calibrated probability in [0.0, 1.0].
        From Jev: the model's own output.
        From LocalFallbackDecisionProvider: a conservative static estimate
        reflecting our uncertainty about the rule quality, not a
        probabilistic output.
    reason
        Human-readable justification.  May be None for the fallback provider.
    provider
        Which DecisionProvider produced this decision.
        "jev" | "local_fallback"
    """

    model: str
    confidence: float
    reason: Optional[str]
    provider: str


# ─────────────────────────────────────────────────────────────────────────────
# Confidence bands
# Used by the application/service layer to determine next action.
# These are DEFAULT values from settings — do NOT hard-code thresholds
# anywhere except here and the Settings class.
# Validate all thresholds experimentally in Phase 10. See docs/evaluation.md.
# ─────────────────────────────────────────────────────────────────────────────

# Import lazily to avoid circular import at module load time
def high_confidence_threshold() -> float:
    from app.core.config import settings
    return settings.high_confidence_threshold


def low_confidence_threshold() -> float:
    from app.core.config import settings
    return settings.low_confidence_threshold
