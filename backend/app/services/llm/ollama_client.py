import logging
from typing import Any

from langchain_ollama import ChatOllama

from app.config import settings

log = logging.getLogger(__name__)


def get_chat_model(
    temperature: float = 0.7,
    model: str | None = None,
    format: str | None = None,
) -> ChatOllama:
    kwargs: dict[str, Any] = {
        "model": model or settings.ollama_model,
        "base_url": settings.ollama_base_url,
        "temperature": temperature,
    }
    if format:
        kwargs["format"] = format
    return ChatOllama(**kwargs)
