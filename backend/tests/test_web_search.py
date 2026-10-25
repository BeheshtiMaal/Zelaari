"""The DuckDuckGo parser is a pure function; the client is bounded and offline-testable."""

import json

import httpx
import pytest

from skills.search import (
    SearchError,
    SearchSettings,
    endpoint,
    parse_duckduckgo,
    parse_searxng,
    search,
)
from skills.websearch import WebSearchInput, build_web_search

PAGE = """
<div class="result results_links">
  <h2 class="result__title">
    <a rel="nofollow" class="result__a"
       href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.test%2Fdocs&amp;rut=abc">
      Example <b>docs</b>
    </a>
  </h2>
  <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.test">
    The <b>official</b> reference.
  </a>
</div>
<div class="result results_links">
  <a rel="nofollow" class="result__a" href="https://second.test/page">Second result</a>
  <a class="result__snippet">Another snippet.</a>
</div>
<a class="result__a" href="javascript:void(0)">Not a result</a>
"""


def transport(page: str = PAGE, status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=page, headers={"content-type": "text/html"})

    return httpx.MockTransport(handler)


def test_the_recorded_page_parses_into_results() -> None:
    results = parse_duckduckgo(PAGE)
    assert [item.url for item in results] == ["https://example.test/docs", "https://second.test/page"]
    assert results[0].title == "Example docs"
    assert results[0].snippet == "The official reference."
    assert results[1].snippet == "Another snippet."


def test_a_page_without_results_is_empty_not_an_error() -> None:
    assert parse_duckduckgo("<html><body>no results</body></html>") == []


def test_results_are_capped() -> None:
    page = "".join(
        f'<a class="result__a" href="https://example.test/{index}">R{index}</a>'
        for index in range(30)
    )
    assert len(parse_duckduckgo(page)) == 8


def test_searxng_payload_parses() -> None:
    payload = {
        "results": [
            {"title": "A", "url": "https://a.test", "content": "first"},
            {"title": "B", "url": "https://b.test"},
            "junk",
        ]
    }
    found = parse_searxng(payload)
    assert [(item.title, item.snippet) for item in found] == [("A", "first"), ("B", "")]


def test_endpoint_requires_https_except_on_localhost() -> None:
    assert endpoint(SearchSettings(provider="searxng", endpoint="https://s.test/")) == "https://s.test"
    assert endpoint(SearchSettings(provider="searxng", endpoint="http://localhost:8080")) == (
        "http://localhost:8080"
    )
    with pytest.raises(SearchError):
        endpoint(SearchSettings(provider="searxng", endpoint="http://s.test"))
    with pytest.raises(SearchError):
        endpoint(SearchSettings(provider="searxng"))


def test_search_uses_the_transport() -> None:
    found = search("q", SearchSettings(), transport=transport())
    assert len(found) == 2


def test_http_failure_is_a_readable_error() -> None:
    with pytest.raises(SearchError) as error:
        search("q", SearchSettings(), transport=transport("nope", status=503))
    assert "503" in str(error.value)


def test_oversized_response_is_refused() -> None:
    with pytest.raises(SearchError) as error:
        search("q", SearchSettings(), transport=transport("x" * 600_000))
    assert "too large" in str(error.value)


def test_unreadable_page_is_reported() -> None:
    with pytest.raises(SearchError) as error:
        search("q", SearchSettings(), transport=transport("<html>changed</html>"))
    assert "no readable results" in str(error.value)


def test_provider_none_is_a_readable_error() -> None:
    with pytest.raises(SearchError) as error:
        search("q", SearchSettings(provider="none"))
    assert "turned off" in str(error.value)


def test_the_tool_returns_json() -> None:
    tool = build_web_search(SearchSettings(), transport=transport())
    payload = json.loads(tool.invoke({"query": "python 3.12 release notes", "limit": 1}))
    assert payload["query"] == "python 3.12 release notes"
    assert len(payload["results"]) == 1


def test_the_tool_reports_a_provider_error_as_text() -> None:
    tool = build_web_search(SearchSettings(provider="none"))
    payload = json.loads(tool.invoke({"query": "anything"}))
    assert "turned off" in payload["error"]


def test_a_query_must_be_one_line() -> None:
    with pytest.raises(ValueError):
        WebSearchInput(query="two\nlines")
    assert WebSearchInput(query="  spaced   query ").query == "spaced query"
