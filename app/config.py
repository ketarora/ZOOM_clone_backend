"""Application configuration.

All settings are read from environment variables (or a .env file) via
pydantic-settings.  No value is ever hard-coded; everything can be
overridden at runtime without touching source code.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./zoom_clone.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    reload: bool = False

    # Public base URL used when generating invite links.
    # Override with the real domain in production (e.g. https://api.example.com).
    base_url: str = "http://localhost:8000"

    # CORS — comma-separated list of allowed origins, or "*" for all.
    cors_origins: str = "*"

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        level = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return level

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
