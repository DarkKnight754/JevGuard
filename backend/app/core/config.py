from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "JevGuard"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: SecretStr

    # ── Cache ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Vector DB (reserved for Phase 6 — RAG Quality Controller) ────────────
    qdrant_url: str = "http://localhost:6333"

    # ── Groq API (FREE — 14,400 req/day for llama-3.1-8b-instant) ────────────
    # Get your free key at: https://console.groq.com
    # Free tier limits (as of Sept 2026):
    #   llama-3.1-8b-instant    — 14,400 req/day, 500K tokens/min  (decisions)
    #   llama-3.3-70b-versatile —  1,000 req/day                   (complex tasks)
    # Leave empty to run entirely on LocalFallbackDecisionProvider.
    groq_api_key: SecretStr
    groq_decision_model: str = "llama-3.1-8b-instant"
    groq_timeout_seconds: float = 10.0

    # ── Ollama (FREE — local open-source LLMs, no API key required) ──────────
    # Runs locally via Docker. Pull models after `docker-compose up`:
    #   docker-compose exec ollama ollama pull llama3.2:3b
    #   docker-compose exec ollama ollama pull qwen2.5-coder:7b
    ollama_base_url: str = "http://ollama:11434"

    # ── Decision Provider ─────────────────────────────────────────────────────
    # "groq"           — GroqDecisionProvider (free, 14,400 req/day)
    # "local_fallback" — LocalFallbackDecisionProvider (no network, deterministic)
    decision_provider: str = "groq"

    # ── HTTP gateway authentication ────────────────────────────────────────────
    gateway_api_key: SecretStr

    # ── Confidence thresholds ─────────────────────────────────────────────────
    # Initial defaults. Validate experimentally in Phase 10.
    # See docs/evaluation.md.
    high_confidence_threshold: float = 0.80
    low_confidence_threshold: float = 0.50


# Single shared instance — import this everywhere
settings = Settings()
