"""A marketplace that is a file in a public repository, not a service.

The catalog is JSON with a version and a list of entries. Fetching is bounded, validation
is strict, and the last good catalog stays cached when a fetch fails: a network problem
must not empty the screen.
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import httpx

from skills.frontmatter import COMMAND, NAME
from skills.types import MarketplaceCatalog, MarketplaceEntry
from tools.atomic import atomic_write
from tools.jail import storage_path

MAX_BYTES = 512_000
MAX_ENTRIES = 200
TIMEOUT = 10.0
CATEGORIES = {"coding", "tests", "web", "docs", "other"}


def validate_url(value: str) -> str:
    """https anywhere; http only for localhost; file only for an absolute path."""
    text = value.strip()
    parsed = urlparse(text)
    if parsed.scheme == "https" and parsed.netloc:
        return text
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return text
    if parsed.scheme == "file" and parsed.path:
        return text
    raise ValueError("Use an https URL (or a local file for testing)")


def file_path(url: str) -> Path:
    """`file:///C:/x` and `file:///tmp/x` both become a real path."""
    parsed = urlparse(url)
    raw = url2pathname(parsed.path)
    if os.name == "nt" and re.match(r"^[/\\][A-Za-z]:", raw):
        raw = raw[1:]
    return Path(raw)


def parse(payload: object) -> MarketplaceCatalog:
    if not isinstance(payload, dict):
        raise ValueError("The catalog must be a JSON object")
    if payload.get("version") != 1:
        raise ValueError("The catalog version must be 1")
    raw = payload.get("skills")
    if not isinstance(raw, list):
        raise ValueError("The catalog needs a skills array")
    if len(raw) > MAX_ENTRIES:
        raise ValueError(f"The catalog is limited to {MAX_ENTRIES} skills")
    entries: list[MarketplaceEntry] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        description = item.get("description")
        url = item.get("url")
        if not isinstance(name, str) or not NAME.match(name) or name in seen:
            continue
        if not isinstance(description, str) or not description.strip():
            continue
        if not isinstance(url, str):
            continue
        try:
            source = validate_url(url)
        except ValueError:
            continue
        command = item.get("command")
        if command is not None and (not isinstance(command, str) or not COMMAND.match(command)):
            command = None
        category = item.get("category")
        entries.append(
            MarketplaceEntry(
                name=name,
                description=" ".join(description.split())[:1024],
                url=source,
                command=command,
                category=category if category in CATEGORIES else "other",
                version=item.get("version") if isinstance(item.get("version"), str) else None,
                author=item.get("author") if isinstance(item.get("author"), str) else None,
            )
        )
        seen.add(name)
    return MarketplaceCatalog(version=1, skills=entries)


def fetch(url: str, *, transport: httpx.BaseTransport | None = None) -> MarketplaceCatalog:
    if url.startswith("file:"):
        path = file_path(url)
        if not path.is_file():
            raise ValueError("That catalog file does not exist")
        raw = path.read_bytes()[: MAX_BYTES + 1]
    else:
        try:
            with httpx.Client(
                timeout=TIMEOUT, follow_redirects=True, transport=transport
            ) as client:
                response = client.get(url, headers={"Accept": "application/json"})
        except httpx.HTTPError as error:
            raise ValueError(f"The catalog could not be fetched ({type(error).__name__})") from None
        if response.status_code != 200:
            raise ValueError(f"The catalog answered {response.status_code}")
        raw = response.content
    if len(raw) > MAX_BYTES:
        raise ValueError("The catalog is too large")
    try:
        document = json.loads(raw)
    except ValueError:
        raise ValueError("The catalog is not valid JSON") from None
    catalog = parse(document)
    catalog.fetched_at = datetime.now(UTC).isoformat()
    catalog.catalog_url = url
    return catalog


def cache(root: Path) -> MarketplaceCatalog | None:
    path = storage_path(root, "marketplace.json")
    try:
        if not path.is_file():
            return None
        raw = path.read_bytes()
        if len(raw) > MAX_BYTES:
            return None
        return MarketplaceCatalog.model_validate_json(raw)
    except (OSError, ValueError):
        return None


def store(root: Path, catalog: MarketplaceCatalog) -> None:
    atomic_write(storage_path(root, "marketplace.json"), catalog.model_dump_json(indent=2))
