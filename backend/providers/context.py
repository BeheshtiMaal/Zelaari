"""Conservative context detection, with explicit precedence and provenance."""

import json
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from providers.base import Context, ProviderRecord


def positive(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def detect_context(model: str, metadata: object = None, error: str = "") -> Context:
    if isinstance(metadata, dict) and isinstance(metadata.get("data"), list):
        for item in metadata.get("data", []):
            if isinstance(item, dict) and item.get("id") == model:
                for field in ("context_window", "context_length", "max_input_tokens"):
                    if tokens := positive(item.get(field)):
                        return Context(tokens=tokens, source="metadata", estimated=False)
    table: dict[str, Any] = json.loads(Path(__file__).with_name("context_table.json").read_text())
    if model in table:
        return Context(tokens=table[model]["tokens"], source="table", estimated=False)
    match = re.search(
        r"(?:maximum context length is|context (?:window|length|limit)(?: is|:)?"
        r"|maximum number of tokens (?:is|allowed is))"
        r"\s*([0-9][0-9,]*)\s*(?:tokens)?",
        error,
        re.I,
    )
    if match and (tokens := positive(int(match[1].replace(",", "")))):
        return Context(tokens=tokens, source="error", estimated=False)
    return Context()


async def model_metadata(record: ProviderRecord, key: SecretStr) -> object:
    headers = {"Authorization": "Bearer " + key.get_secret_value()}
    path = "/models"
    if record.kind == "anthropic":
        path = "/v1/models"
        headers = {"x-api-key": key.get_secret_value(), "anthropic-version": "2023-06-01"}
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
            response = await client.get((record.base_url or "") + path, headers=headers)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        return None
