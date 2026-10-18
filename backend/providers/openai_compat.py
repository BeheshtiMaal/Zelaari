"""Phase 1 opt-in provider, configured explicitly via the launch environment."""

import os
from urllib.parse import urlsplit

from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def configured_model() -> ChatOpenAI:
    key = os.environ.get("CODEHARNESS_API_KEY", "")
    base = os.environ.get("CODEHARNESS_BASE_URL", "")
    name = os.environ.get("CODEHARNESS_MODEL", "")
    if not key or not name or urlsplit(base).scheme not in {"http", "https"}:
        raise ValueError(
            "Configure CODEHARNESS_API_KEY, CODEHARNESS_BASE_URL and CODEHARNESS_MODEL"
        )
    return ChatOpenAI(
        model=name,
        base_url=base,
        api_key=SecretStr(key),
        use_responses_api=False,
        streaming=True,
        max_retries=0,
        timeout=30,
    )
