"""Application settings for the local backend service."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Multi-Agent Assistant"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    openhands_mode: str = Field(
        default="mock",
        description="Execution mode for the OpenHands adapter: mock, http, or disabled.",
    )
    openhands_base_url: str | None = Field(
        default=None,
        description="Optional OpenHands-compatible HTTP endpoint.",
    )
    openhands_timeout_seconds: int = Field(default=30)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings to avoid reloading environment variables."""
    return Settings()

