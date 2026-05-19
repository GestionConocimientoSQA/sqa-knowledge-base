"""App configuration via Pydantic Settings (12-factor)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime config exclusively from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SQA_KB_",
        extra="ignore",
    )

    app_env: str = Field(default="dev", description="dev | staging | prod | test")
    api_v1_prefix: str = "/api/v1"

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
