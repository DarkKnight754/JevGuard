from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.decision.contracts import RequestState
from app.schemas.decision import RouteRequestBody, RouteResponseBody
from app.services.decision_service import DecisionService

log = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/decisions/route",
    response_model=RouteResponseBody,
    tags=["Decisions"],
    summary="Route a request to the appropriate LLM category",
    description=(
        "Accepts pre-computed request features and returns a routing decision. "
        "Uses JevDecisionProvider when configured and available; "
        "falls back to LocalFallbackDecisionProvider automatically. "
        "Every decision is written to the audit log regardless of provider."
    ),
)
async def route_request(
    body: RouteRequestBody,
    db: AsyncSession = Depends(get_db),
    x_request_id: Optional[str] = Header(
        default=None,
        description="Client-supplied correlation ID. Generated if not provided.",
    ),
) -> RouteResponseBody:
    request_id = x_request_id or str(uuid.uuid4())

    # Translate the public HTTP schema → internal contract
    # The rest of the application only sees RequestState and RoutingDecision
    state = RequestState(
        token_count=body.token_count,
        has_code=body.has_code,
        has_vision=body.has_vision,
        requires_reasoning=body.requires_reasoning,
        tool_call_type=body.tool_call_type,
        retrieved_doc_count=body.retrieved_doc_count,
        query_complexity_score=body.query_complexity_score,
    )

    log.info(
        "decisions.route.request",
        request_id=request_id,
        token_count=state.token_count,
    )

    service = DecisionService(db=db)
    decision, latency_ms = await service.route(state, request_id=request_id)

    return RouteResponseBody(
        request_id=request_id,
        model=decision.model,
        confidence=decision.confidence,
        reason=decision.reason,
        provider=decision.provider,
        latency_ms=latency_ms,
    )
