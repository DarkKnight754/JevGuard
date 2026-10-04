"""
GroqDecisionProvider — the primary free decision provider for JevGuard.

Uses Groq's free-tier LLaMA inference to make structured routing decisions.
Falls back automatically to LocalFallbackDecisionProvider via DecisionService
on any error.

Free tier: 14,400 requests/day on llama-3.1-8b-instant.
Get your key at: https://console.groq.com
"""

from __future__ import annotations

import dataclasses
import structlog

from app.decision.base import DecisionProvider, DecisionProviderError
from app.decision.contracts import RequestState, RoutingDecision
from app.decision.groq_client import GroqDecisionClient

log = structlog.get_logger(__name__)

_VALID_MODELS = {"small", "large", "code", "vision", "reasoning"}


class GroqDecisionProvider(DecisionProvider):
    """
    Calls Groq's free LLaMA API to produce a calibrated routing decision.

    On any failure (API error, timeout, malformed JSON, unexpected model value),
    raises DecisionProviderError so DecisionService can activate the
    LocalFallbackDecisionProvider cleanly.
    """

    def __init__(self, client: GroqDecisionClient | None = None) -> None:
        # Injectable for testing — pass a mock client to avoid network calls
        self._client = client or GroqDecisionClient()

    @property
    def provider_name(self) -> str:
        return "groq"

    async def route_request(self, state: RequestState) -> RoutingDecision:
        state_dict = dataclasses.asdict(state)
        # Compact pipe-delimited string to minimise tokens sent to Groq
        state_text = " | ".join(f"{k}={v}" for k, v in state_dict.items())

        log.info("groq_provider.routing", **state_dict)

        try:
            data = await self._client.get_routing_decision(state_text)
        except Exception as exc:
            log.error("groq_provider.api_failed", error=str(exc), exc_info=True)
            raise DecisionProviderError(
                f"Groq provider failed to return a decision: {exc}"
            ) from exc

        # Validate response shape
        model = str(data.get("model", "")).strip().lower()
        if model not in _VALID_MODELS:
            raise DecisionProviderError(
                f"Groq returned unexpected model '{model}'. "
                f"Expected one of {sorted(_VALID_MODELS)}."
            )

        try:
            confidence = float(data["confidence"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DecisionProviderError(
                f"Groq response missing valid 'confidence' field: {data}"
            ) from exc

        reason: str | None = data.get("reason")

        decision = RoutingDecision(
            model=model,
            confidence=max(0.0, min(1.0, confidence)),   # clamp to [0,1]
            reason=reason,
            provider=self.provider_name,
        )
        log.info(
            "groq_provider.decision",
            model=model,
            confidence=decision.confidence,
            reason=reason,
        )
        return decision
