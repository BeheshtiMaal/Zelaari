"""A small, bounded web-search client with a pluggable provider.

The default is DuckDuckGo's HTML endpoint: no account, no key, no configuration. The
parser is a pure function tested against a recorded page; when the page changes, the tool
reports that it could not read the results instead of inventing them.
"""

import html
import json
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

MAX_BYTES = 512_000
TIMEOUT = 10.0
MAX_RESULTS = 8
USER_AGENT = "CodeHarness/0.1 (local coding agent)"
FIXTURE_ENV = "CODEHARNESS_SEARCH_FIXTURE"
"""A recorded results page. Only the desktop suite sets it, so its runs stay offline."""

ANCHOR = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
CLASS = re.compile(r'class\s*=\s*"([^"]*)"', re.IGNORECASE)
HREF = re.compile(r'href\s*=\s*"([^"]*)"', re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    snippet: str = ""


class SearchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["duckduckgo", "searxng", "none"] = "duckduckgo"
    endpoint: str | None = Field(default=None, max_length=2048)
    """Only for `searxng`; ignored by the keyless default."""


class SearchError(Exception):
    """A search that could not run or could not be parsed. Never a traceback to the UI."""


def text_of(fragment: str) -> str:
    return " ".join(html.unescape(TAG.sub(" ", fragment)).split())


def real_url(href: str) -> str | None:
    """DuckDuckGo wraps results in `/l/?uddg=...`; return the destination."""
    if not href:
        return None
    if href.startswith("//"):
        href = f"https:{href}"
    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg")
        if not target:
            return None
        href = target[0]
        parsed = urlparse(href)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return href


def parse_duckduckgo(page: str) -> list[SearchResult]:
    """Titles from `result__a`, snippets from `result__snippet`, capped."""
    results: list[SearchResult] = []
    for attrs, body in ANCHOR.findall(page):
        classes = CLASS.search(attrs)
        if classes is None:
            continue
        names = classes.group(1).split()
        if "result__a" in names:
            href = HREF.search(attrs)
            url = real_url(href.group(1)) if href else None
            title = text_of(body)
            if url and title:
                results.append(SearchResult(title=title, url=url))
        elif "result__snippet" in names and results:
            snippet = text_of(body)
            if snippet and not results[-1].snippet:
                results[-1] = results[-1].model_copy(update={"snippet": snippet})
        if len(results) >= MAX_RESULTS:
            break
    return results[:MAX_RESULTS]


def parse_searxng(payload: object) -> list[SearchResult]:
    if not isinstance(payload, dict):
        raise SearchError("the search endpoint did not return a JSON object")
    raw = payload.get("results")
    if not isinstance(raw, list):
        return []
    results: list[SearchResult] = []
    for item in raw[:MAX_RESULTS]:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = item.get("title")
        if not isinstance(url, str) or not isinstance(title, str):
            continue
        snippet = item.get("content")
        results.append(
            SearchResult(
                title=" ".join(title.split()),
                url=url,
                snippet=" ".join(snippet.split()) if isinstance(snippet, str) else "",
            )
        )
    return results


def endpoint(settings: SearchSettings) -> str:
    if not settings.endpoint:
        raise SearchError("no search endpoint is configured")
    parsed = urlparse(settings.endpoint)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise SearchError("the search endpoint must use https")
    return settings.endpoint.rstrip("/")


def search(
    query: str,
    settings: SearchSettings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> list[SearchResult]:
    """One bounded request. Raises `SearchError` for anything the person should read."""
    if settings.provider == "none":
        raise SearchError("web search is turned off in settings")
    fixture = os.environ.get(FIXTURE_ENV)
    if fixture:
        page = Path(fixture).read_text(encoding="utf-8", errors="replace")[:MAX_BYTES]
        results = parse_duckduckgo(page)
        if not results:
            raise SearchError("the recorded search page had no readable results")
        return results
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}
    try:
        with httpx.Client(
            timeout=TIMEOUT, follow_redirects=True, transport=transport, headers=headers
        ) as client:
            if settings.provider == "duckduckgo":
                response = client.get(
                    "https://html.duckduckgo.com/html/", params={"q": query}
                )
            else:
                response = client.get(
                    f"{endpoint(settings)}/search", params={"q": query, "format": "json"}
                )
    except httpx.HTTPError as error:
        raise SearchError(f"the search request failed ({type(error).__name__})") from None
    if response.status_code != 200:
        raise SearchError(f"the search provider answered {response.status_code}")
    body = response.content
    if len(body) > MAX_BYTES:
        raise SearchError("the search response was too large")
    if settings.provider == "searxng":
        try:
            return parse_searxng(json.loads(body))
        except ValueError:
            raise SearchError("the search endpoint returned invalid JSON") from None
    page = body.decode(response.encoding or "utf-8", errors="replace")
    results = parse_duckduckgo(page)
    if not results:
        raise SearchError("the search provider returned no readable results")
    return results
