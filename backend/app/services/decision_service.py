"""
DecisionService — orchestrates the decision pipeline.

Provider selection order (Phase 1–2):
  1. GroqDecisionProvider   — free, 14,400 req/day, LLaMA via Groq API
  2. LocalFallbackDecisionProvider — deterministic, no external calls

The service auto-selects based on config + API key presence.
"""

from __future__ import annotations

import dataclasses
import time
import uuid
import structlog

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.decision.base import DecisionProvider, DecisionProviderError
from app.decision.contracts import RequestState, RoutingDecision
from app.decision.fallback_provider import LocalFallbackDecisionProvider
from app.decision.groq_provider import GroqDecisionProvider
from app.models.audit import DecisionAuditLog

log = structlog.get_logger(__name__)


def _build_primary_provider() -> DecisionProvider:
    """
    Build the primary DecisionProvider.

    Automatically degrades to LocalFallbackDecisionProvider when:
    - DECISION_PROVIDER=local_fallback  (explicit override)
    - GROQ_API_KEY is not set           (safe default for local dev / CI)
    """
    if settings.decision_provider == "local_fallback":
        log.info("decision_service.provider_selected",
                 provider="local_fallback", reason="config override")
        return LocalFallbackDecisionProvider()

    if not settings.groq_api_key:
        log.warning(
            "decision_service.provider_selected",
            provider="local_fallback",
            reason="GROQ_API_KEY not set — get a free key at https://console.groq.com",
        )
        return LocalFallbackDecisionProvider()

    log.info("decision_service.provider_selected",
             provider="groq", model=settings.groq_decision_model)
    return GroqDecisionProvider()


class DecisionService:
    """Stateless per-request service. Instantiated via FastAPI DI."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._primary: DecisionProvider = _build_primary_provider()
        self._fallback: DecisionProvider = LocalFallbackDecisionProvider()

    async def route(
        self,
        state: RequestState,
        request_id: str | None = None,
    ) -> tuple[RoutingDecision, int]:
        """
        Returns (RoutingDecision, latency_ms).

        Tries primary provider; falls back to LocalFallbackDecisionProvider on
        DecisionProviderError. Writes an audit record regardless of provider.
        """
        request_id = request_id or str(uuid.uuid4())
        start_ns = time.monotonic_ns()

        try:
            decision = await self._primary.route_request(state)
        except DecisionProviderError as exc:
            log.warning(
                "decision_service.primary_failed",
                error=str(exc),
                request_id=request_id,
                falling_back_to="local_fallback",
            )
            decision = await self._fallback.route_request(state)

        latency_ms = (time.monotonic_ns() - start_ns) // 1_000_000

        await self._write_audit(
            request_id=request_id,
            state=state,
            decision=decision,
            latency_ms=latency_ms,
        )

        log.info(
            "decision_service.complete",
            request_id=request_id,
            model=decision.model,
            confidence=decision.confidence,
            provider=decision.provider,
            latency_ms=latency_ms,
        )
        return decision, int(latency_ms)

    async def _write_audit(
        self,
        request_id: str,
        state: RequestState,
        decision: RoutingDecision,
        latency_ms: int,
    ) -> None:
        record = DecisionAuditLog(
            request_id=request_id,
            provider=decision.provider,
            model_selected=decision.model,
            confidence=decision.confidence,
            reason=decision.reason,
            input_state=dataclasses.asdict(state),
            latency_ms=int(latency_ms),
        )
        self._db.add(record)
        await self._db.flush()
