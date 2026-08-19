from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables (or .env)."""

    model_config = SettingsConfigDict(env_prefix="CHAINWISE_", env_file=".env", extra="ignore")

    app_name: str = "chainwise"
    environment: str = "local"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
