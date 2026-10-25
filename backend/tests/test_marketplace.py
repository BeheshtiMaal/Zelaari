"""The marketplace is a validated JSON file, cached, and never empties on a bad fetch."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from skills import marketplace

HEADERS = {"Authorization": "Bearer token"}

CATALOG = {
    "version": 1,
    "skills": [
        {
            "name": "team-rules",
            "description": "Our house conventions.",
            "url": "https://example.test/skills/team-rules.git",
            "command": "/team",
            "category": "coding",
            "version": "1.2.0",
            "author": "Team",
        },
        {"name": "Bad Name", "description": "x", "url": "https://example.test/x"},
        {"name": "no-url", "description": "x"},
        {"name": "team-rules", "description": "duplicate", "url": "https://example.test/dup"},
    ],
}


def test_entries_are_validated_and_deduplicated() -> None:
    catalog = marketplace.parse(CATALOG)
    assert [item.name for item in catalog.skills] == ["team-rules"]
    assert catalog.skills[0].command == "/team"
    assert catalog.skills[0].version == "1.2.0"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"version": 2, "skills": []},
        {"version": 1},
        {"version": 1, "skills": [{}] * 201},
    ],
)
def test_a_bad_catalog_is_refused(payload: object) -> None:
    with pytest.raises(ValueError):
        marketplace.parse(payload)


@pytest.mark.parametrize(
    "url",
    ["https://example.test/c.json", "http://localhost:8080/c.json", "file:///tmp/c.json"],
)
def test_allowed_urls(url: str) -> None:
    assert marketplace.validate_url(url) == url


@pytest.mark.parametrize("url", ["http://example.test/c.json", "ftp://x/c.json", ""])
def test_refused_urls(url: str) -> None:
    with pytest.raises(ValueError):
        marketplace.validate_url(url)


def test_a_local_catalog_is_read(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    catalog = marketplace.fetch(path.as_uri())
    assert catalog.skills[0].name == "team-rules"
    assert catalog.fetched_at is not None


def test_an_http_failure_is_readable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(ValueError, match="500"):
        marketplace.fetch("https://example.test/c.json", transport=httpx.MockTransport(handler))


def test_a_large_catalog_is_refused() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 600_000)

    with pytest.raises(ValueError, match="too large"):
        marketplace.fetch("https://example.test/c.json", transport=httpx.MockTransport(handler))


def test_the_cache_round_trips_and_survives_damage(tmp_path: Path) -> None:
    catalog = marketplace.parse(CATALOG)
    marketplace.store(tmp_path, catalog)
    assert marketplace.cache(tmp_path) is not None
    (tmp_path / ".harness" / "marketplace.json").write_text("{broken", encoding="utf-8")
    assert marketplace.cache(tmp_path) is None


def test_the_route_sets_the_url_and_caches(tmp_path: Path) -> None:
    source = tmp_path / "catalog.json"
    source.write_text(json.dumps(CATALOG), encoding="utf-8")
    workspace = tmp_path / "workspace"
    (workspace / ".harness").mkdir(parents=True)
    with TestClient(create_app("token")) as http:
        saved = http.put(
            "/skills/marketplace",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"url": source.as_uri()},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["skills"][0]["name"] == "team-rules"
        read = http.get(
            "/skills/marketplace", headers=HEADERS, params={"workspace": str(workspace)}
        )
        assert read.status_code == 200
        assert read.json()["catalog_url"] == source.as_uri()
        assert read.json()["fetched_at"]
        overview = http.get("/skills", headers=HEADERS, params={"workspace": str(workspace)})
        assert overview.json()["catalog_url"] == source.as_uri()
    assert (workspace / ".harness" / "marketplace.json").is_file()


def test_a_bad_url_is_refused_by_the_route(tmp_path: Path) -> None:
    with TestClient(create_app("token")) as http:
        response = http.put(
            "/skills/marketplace",
            headers=HEADERS,
            params={"workspace": str(tmp_path)},
            json={"url": "http://example.test/catalog.json"},
        )
    assert response.status_code == 400
