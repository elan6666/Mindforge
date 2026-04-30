"""Application settings for the local backend service."""

from functools import lru_cache
from pathlib import Path

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

    app_name: str = "Mindforge"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    openhands_mode: str = Field(
        default="mock",
        description="Execution mode for the OpenHands adapter: mock, http, model-api, or disabled.",
    )
    openhands_base_url: str | None = Field(
        default=None,
        description="Optional OpenHands-compatible HTTP endpoint.",
    )
    openhands_timeout_seconds: int = Field(default=30)
    github_api_base_url: str = Field(
        default="https://api.github.com",
        description="Base URL for GitHub read-only API access.",
    )
    github_token: str | None = Field(
        default=None,
        description="Optional GitHub token used for authenticated read-only requests.",
    )
    github_timeout_seconds: int = Field(default=20)
    academic_context_timeout_seconds: int = Field(default=15)
    model_api_timeout_seconds: int = Field(default=60)
    model_api_max_tokens: int = Field(default=1200)
    sqlite_db_path: str = Field(
        default=str(Path("app") / "data" / "mindforge.db"),
        description="SQLite database path for task history and approvals.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings to avoid reloading environment variables."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings after environment mutations in tests."""
    get_settings.cache_clear()
