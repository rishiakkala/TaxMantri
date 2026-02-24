"""
config.py — TaxMantri application settings.

Usage:
    from backend.config import settings
    print(settings.database_url)

Never use FastAPI Depends() for settings — import directly as a module-level singleton.
"""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Silently ignore any extra env vars
    )

    # --- Database ---
    # Format: postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME
    database_url: str = "postgresql+asyncpg://taxmantri:taxmantri@localhost:5432/taxmantri"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"

    # --- Security ---
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "change-me-in-production-at-least-32-chars"

    # --- External APIs ---
    mistral_api_key: str = ""

    # --- CORS ---
    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # --- Application ---
    debug: bool = True
    app_version: str = "0.1.0"

    @property
    def cors_origins_list(self) -> List[str]:
        """Split comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Module-level singleton — import this throughout the codebase
settings = Settings()
