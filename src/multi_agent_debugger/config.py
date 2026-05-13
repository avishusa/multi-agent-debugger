"""Application configuration loaded from environment variables.

Single source of truth for all runtime configuration. Read at startup,
validated once, exposed as an immutable `Settings` instance via
`get_settings()`. Never use `os.environ` directly anywhere else.

The fields here mirror `.env.example` one-to-one. To add a new config
value: add it here with a type and default, then add it to `.env.example`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, loaded from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # --- Secrets ----------------------------------------------------------
    gemini_api_key: SecretStr = Field(
        ...,
        description="Google AI Studio API key. Required.",
    )
    mongodb_uri: SecretStr = Field(
        ...,
        description="MongoDB Atlas connection string. Required.",
    )

    # --- Database ---------------------------------------------------------
    db_name: str = Field(
        default="multi_agent_debugger",
        description="Mongo database name. Kept separate from sibling projects.",
    )
    mongo_timeout_ms: int = Field(
        default=5000,
        ge=500,
        le=60000,
        description="Server selection timeout for MongoDB in milliseconds.",
    )

    # --- LLM --------------------------------------------------------------
    llm_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model id. Swap to `gemini-2.5-flash-lite` for higher RPM.",
    )

    # --- Observability ----------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Root logger level.",
    )
    log_format: Literal["pretty", "json"] = Field(
        default="pretty",
        description="`pretty` for colored dev console, `json` for production logs.",
    )

    # --- Agent behavior ---------------------------------------------------
    memory_retrieval_limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Max past Facts/Decisions retrieved from the graph per agent call.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton `Settings` instance.

    Cached so the `.env` file is parsed once per process. Tests can call
    `get_settings.cache_clear()` to force a reload after monkeypatching
    environment variables.
    """
    return Settings()  # type: ignore[call-arg]
