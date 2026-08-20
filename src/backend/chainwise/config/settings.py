from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables (or .env)."""

    model_config = SettingsConfigDict(env_prefix="CHAINWISE_", env_file=".env", extra="ignore")

    app_name: str = "chainwise"
    environment: str = "local"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    network: str = "ethereum-mainnet"

    database_url: str = "postgresql://chainwise:chainwise@localhost:5432/chainwise"
    # No CHAINWISE_ prefix: matches the env var name OpenRouter's own docs use.
    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="openai/gpt-4.1-mini", validation_alias="OPENROUTER_MODEL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
