"""
LocalFallbackDecisionProvider — deterministic, rule-based routing.

Used when:
  - Jev API is unavailable or times out
  - DECISION_PROVIDER=local_fallback in config
  - TYPESAFE_API_KEY is not set
  - Unit tests that must not make network calls

Guarantees
----------
- No model calls, no external dependencies, no network I/O.
- Always returns a RoutingDecision; never raises DecisionProviderError.
- Confidence values are static estimates of our uncertainty about the rule
  quality — they are NOT probabilistic model outputs.  They are deliberately
  conservative.  Validate against evaluation data in Phase 10.
"""

from __future__ import annotations

import structlog

from app.decision.base import DecisionProvider
from app.decision.contracts import RequestState, RoutingDecision

log = structlog.get_logger(__name__)


class LocalFallbackDecisionProvider(DecisionProvider):

    @property
    def provider_name(self) -> str:
        return "local_fallback"

    async def route_request(self, state: RequestState) -> RoutingDecision:
        model, confidence, reason = self._apply_rules(state)

        decision = RoutingDecision(
            model=model,
            confidence=confidence,
            reason=reason,
            provider=self.provider_name,
        )
        log.info(
            "fallback_provider.decision",
            model=model,
            confidence=confidence,
            reason=reason,
            token_count=state.token_count,
        )
        return decision

    # ─────────────────────────────────────────────────────────────────────────
    # Rule set
    # Rules are ordered: first match wins.
    # When in doubt the default is "large" — safe but not cheap.
    # Replace with Jev-calibrated thresholds after Phase 10 evaluation.
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_rules(
        self, state: RequestState
    ) -> tuple[str, float, str]:

        # 1. Vision input — needs a multimodal model regardless of anything else
        if state.has_vision:
            return (
                "vision",
                0.70,
                "Request contains vision input — multimodal model required.",
            )

        # 2. Code without complex reasoning — prefer a code-specialized model
        if state.has_code and not state.requires_reasoning:
            return (
                "code",
                0.72,
                "Request contains code content; no deep reasoning flag — "
                "prefer code-specialized model.",
            )

        # 3. Large context — small models lose coherence beyond ~8k tokens
        if state.token_count > 8_000:
            return (
                "large",
                0.68,
                f"Token count {state.token_count} exceeds 8 000 — "
                "use large-context model.",
            )

        # 4. Explicit reasoning flag OR high complexity score
        if state.requires_reasoning or state.query_complexity_score > 0.70:
            return (
                "reasoning",
                0.65,
                f"reasoning_flag={state.requires_reasoning}, "
                f"complexity={state.query_complexity_score:.2f} — "
                "use reasoning-capable model.",
            )

        # 5. Default — small model covers the remaining low-complexity cases
        return (
            "small",
            0.60,
            "No special routing signals detected — default to small model.",
        )
