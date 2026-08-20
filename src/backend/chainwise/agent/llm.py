from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from chainwise.config import get_settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm() -> ChatOpenAI:
    """Chat model pointed at OpenRouter (OpenAI-compatible API)."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openrouter_model,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(settings.openrouter_api_key),
    )
