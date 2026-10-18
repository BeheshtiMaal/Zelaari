"""Provider metadata without credentials in serializable records."""

from typing import Literal

from pydantic import BaseModel


class ProviderRecord(BaseModel):
    name: str
    model: str
    kind: Literal["demo", "openai-compatible"]
    base_url: str | None = None
