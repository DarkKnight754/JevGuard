"""
DecisionAuditLog — append-only record of every routing decision.

Design principles
-----------------
- Never mutate records after insertion.  Append-only.
- Every routing decision is logged regardless of provider.
- input_state is stored as JSON so we can replay or analyse decisions later.
- latency_ms enables the Phase 10 benchmark (baseline vs JevGuard latency).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionAuditLog(Base):
    __tablename__ = "decision_audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Correlation ID from the upstream HTTP request (X-Request-Id header)
    request_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    # "jev" | "local_fallback"
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    # Logical model category selected: "small" | "large" | "code" | …
    model_selected: Mapped[str] = mapped_column(String(64), nullable=False)
    # Calibrated confidence from the provider [0.0, 1.0]
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Human-readable justification (may be None for fallback provider)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Full RequestState serialised as JSON for replay / analysis
    input_state: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    # End-to-end time from service entry to DB write (ms)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
