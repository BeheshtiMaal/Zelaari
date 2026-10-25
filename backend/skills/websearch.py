"""`web_search`: one query in, a bounded list of sources out, an approval before either."""

import json
from typing import Any

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, field_validator

from skills.search import MAX_RESULTS, SearchError, SearchSettings, search


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=400)
    limit: int = Field(default=5, ge=1, le=MAX_RESULTS)

    @field_validator("query")
    @classmethod
    def one_line(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("Query is empty")
        if "\n" in value or "\r" in value:
            raise ValueError("A query must be a single line")
        return text


def build_web_search(
    settings: SearchSettings, *, transport: httpx.BaseTransport | None = None
) -> BaseTool:
    def web_search(query: str, limit: int = 5) -> str:
        try:
            results = search(query, settings, transport=transport)[:limit]
        except SearchError as error:
            return json.dumps({"query": query, "error": str(error)}, ensure_ascii=False)
        payload: dict[str, Any] = {
            "query": query,
            "provider": settings.provider,
            "results": [item.model_dump() for item in results],
        }
        return json.dumps(payload, ensure_ascii=False)

    return StructuredTool.from_function(
        func=web_search,
        name="web_search",
        description=(
            "Search the web for current facts. Every query needs the person's approval, "
            "and the query they edit is the one that runs. Returns titles, URLs and "
            "snippets; cite the URLs you use."
        ),
        args_schema=WebSearchInput,
    )
