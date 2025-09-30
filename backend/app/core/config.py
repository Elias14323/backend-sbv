"""Application configuration using Pydantic settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    redis_url: str
    mistral_api_key: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance, validating required configuration."""

    return Settings()


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
