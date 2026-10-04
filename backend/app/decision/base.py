"""
DecisionProvider — abstract interface for all routing decision providers.

The rest of JevGuard (routes, services, tests) imports ONLY from this module
and from contracts.py.  No application-layer module ever imports
JevDecisionProvider or LocalFallbackDecisionProvider directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.decision.contracts import RequestState, RoutingDecision


class DecisionProvider(ABC):
    """
    Abstract base for all decision providers.

    Implementations must be async-safe and must never raise arbitrary
    exceptions to callers.  On failure, raise DecisionProviderError so the
    orchestrating service can catch it and trigger the fallback path cleanly.
    """

    @abstractmethod
    async def route_request(self, state: RequestState) -> RoutingDecision:
        """
        Given a compact request state, return a routing decision.

        Must never propagate low-level transport or API errors — wrap them in
        DecisionProviderError so the service layer can handle them uniformly.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable string identifier included in every RoutingDecision."""
        ...


class DecisionProviderError(Exception):
    """
    Raised by a DecisionProvider when it cannot produce a decision.

    The service layer catches this and triggers the fallback provider.
    Include the original exception as __cause__ for observability.
    """
    pass
