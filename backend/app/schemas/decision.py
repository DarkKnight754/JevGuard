"""
Public HTTP request/response schemas for the decision endpoints.

These are NOT the same as the internal contracts (RequestState, RoutingDecision).
The service layer translates between them.  This separation lets us evolve the
HTTP API and the internal model independently.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RouteRequestBody(BaseModel):
    """
    Body for POST /api/v1/decisions/route.

    Callers are responsible for feature engineering before sending.
    Do not send raw user text — compute the scalar features upstream.
    """

    token_count: int = Field(
        ..., ge=0, description="Estimated token count of the full request context."
    )
    has_code: bool = Field(
        default=False,
        description="True if the request contains a code block.",
    )
    has_vision: bool = Field(
        default=False,
        description="True if the request contains image input.",
    )
    requires_reasoning: bool = Field(
        default=False,
        description="True if multi-step reasoning is required.",
    )
    tool_call_type: Optional[str] = Field(
        default=None,
        description="Category of tool being invoked: delete | write | read | execute",
    )
    retrieved_doc_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidate RAG documents retrieved. Zero until Phase 6.",
    )
    query_complexity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Pre-computed deterministic complexity score [0.0, 1.0].",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "token_count": 512,
            "has_code": True,
            "has_vision": False,
            "requires_reasoning": False,
            "tool_call_type": None,
            "retrieved_doc_count": 0,
            "query_complexity_score": 0.45,
        }
    }}


class RouteResponseBody(BaseModel):
    """
    Response from POST /api/v1/decisions/route.

    The application always sees this shape.  Never a provider-internal type.
    """

    request_id: str = Field(description="Correlation ID for this request.")
    model: str = Field(description="Logical model category selected.")
    confidence: float = Field(description="Provider confidence [0.0, 1.0].")
    reason: Optional[str] = Field(description="Human-readable routing rationale.")
    provider: str = Field(description="Which provider made the decision.")
    latency_ms: int = Field(description="End-to-end decision latency in ms.")
