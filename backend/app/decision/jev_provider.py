# backend/app/decision/openjev_provider.py

from app.decision.base import DecisionProvider, DecisionProviderError
from app.decision.contracts import RequestState, RoutingDecision
from app.decision.jev_client import JevClient          # same client, different URL
from app.decision.jev_provider import JevDecisionProvider

class OpenJevDecisionProvider(JevDecisionProvider):
    """
    Runs OpenJev locally via GGUF + llama.cpp + shim.py.
    API format is identical to hosted Jev — only the base URL differs.
    
    Hardware required: RTX 3090/4090 (24GB VRAM) for GGUF Q4_K_M.
    Setup: see docs/openjev-setup.md
    """

    def __init__(self) -> None:
        from app.core.config import settings
        # Point the same JevClient at the local OpenJev shim
        client = JevClient(base_url=settings.openjev_base_url,
                           model_id="openjev",
                           api_key="")    # no key needed for local
        super().__init__(client=client)

    @property
    def provider_name(self) -> str:
        return "openjev"
