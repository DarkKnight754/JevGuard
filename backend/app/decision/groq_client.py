"""
Groq API client for structured routing decisions.

Why Groq?
---------
- Completely FREE: 14,400 requests/day on llama-3.1-8b-instant
- Extremely fast inference (purpose-built for low-latency)
- JSON mode for structured output — perfect for decision-making
- OpenAI-compatible SDK, widely documented
- Get your free key at: https://console.groq.com

This module is the ONLY place that knows about the Groq wire format.
The rest of JevGuard programs against DecisionProvider → RoutingDecision only.

Free tier model reference (Sept 2026)
--------------------------------------
Model                        Req/day   Tokens/min  Context
llama-3.1-8b-instant         14,400    500,000     131,072  ← used here (decisions)
llama-3.3-70b-versatile       1,000    100,000     131,072  ← Phase 4 (complex tasks)
llama-3.1-70b-versatile       1,000    100,000     131,072
gemma2-9b-it                 14,400    15,000       8,192
"""

from __future__ import annotations

import json
import structlog
from groq import AsyncGroq

from app.core.config import settings

log = structlog.get_logger(__name__)

# Valid routing categories — must match fallback_provider.py and model_routing.yaml
_MODEL_CHOICES = ["small", "large", "code", "vision", "reasoning"]

# System prompt for the routing decision.
# Explicit, short, and returns only valid JSON — critical for reliability.
_ROUTING_SYSTEM_PROMPT = f"""You are a request routing decision engine for JevGuard.

Given compact request features, decide which LLM category should handle the request.

Return ONLY a JSON object with exactly these three fields:
{{
  "model": "<one of: {', '.join(_MODEL_CHOICES)}>",
  "confidence": <float 0.0–1.0>,
  "reason": "<one sentence>"
}}

Routing rules:
- vision    : has_vision=true → always route here, regardless of other signals
- code      : has_code=true AND requires_reasoning=false
- large     : token_count > 8000 OR large document context
- reasoning : requires_reasoning=true OR query_complexity_score > 0.70
- small     : everything else — simple, low-complexity, short context

No markdown. No extra keys. No explanation outside the JSON object.
"""


class GroqDecisionClient:
    """
    Thin async wrapper around the Groq chat completions API.

    Calls groq with JSON mode to get a structured routing decision.
    Knows nothing about JevGuard routing logic — that lives in
    GroqDecisionProvider.
    """

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key.get_secret_value())
        self._model = settings.groq_decision_model

    async def get_routing_decision(self, state_text: str) -> dict:
        """
        Send state features to Groq and return parsed JSON decision dict.

        Returns a dict with keys: model, confidence, reason.
        Raises groq.APIError or json.JSONDecodeError on failure — callers
        wrap these in DecisionProviderError.
        """
        log.debug("groq_client.request", model=self._model, state_chars=len(state_text))

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
                {"role": "user", "content": f"Route this request:\n{state_text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,      # Deterministic — routing should not be random
            max_tokens=150,       # Decisions are tiny; cap tokens to save quota
        )

        raw: str = response.choices[0].message.content
        log.debug("groq_client.response", raw=raw)

        return json.loads(raw)
