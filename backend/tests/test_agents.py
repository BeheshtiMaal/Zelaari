"""`.harness/agents/<name>.md`: parsed, capped, read-only, and written through approval."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agents import loader, tools
from server.app import create_app
from tools.jail import storage_path

HEADERS = {"Authorization": "Bearer token"}
TEXT = """---
name: api-reviewer
description: Reviews the HTTP layer for contract drift.
tools: read_file, grep, write_file
---

Read the route modules and report drift. Never edit.
"""


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".harness" / "agents").mkdir(parents=True)
    return tmp_path


def client() -> TestClient:
    return TestClient(create_app("token"))


def approve(http: TestClient, record: dict[str, object]) -> None:
    request = record["request"]
    assert isinstance(request, dict)
    response = http.post(
        f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
        headers=HEADERS,
        json={"decision": "approve"},
    )
    assert response.status_code == 200, response.text


def write(workspace: Path, name: str, text: str) -> None:
    storage_path(workspace, f"agents/{name}.md").write_text(text, encoding="utf-8")


def test_a_file_parses_into_a_record_and_instructions() -> None:
    parsed = loader.parse(TEXT, "api-reviewer")
    assert not isinstance(parsed, str)
    record, instructions = parsed
    assert record.name == "api-reviewer"
    assert record.description.startswith("Reviews the HTTP")
    # write_file is outside the ceiling and is dropped, not passed through.
    assert record.tools == ["grep", "read_file"]
    assert "report drift" in instructions


def test_a_name_mismatch_is_a_problem() -> None:
    problem = loader.parse(TEXT, "other")
    assert isinstance(problem, str)
    assert "does not match" in problem


def test_a_missing_description_or_body_is_a_problem() -> None:
    assert isinstance(loader.parse("---\nname: a\ndescription: d\n---\n", "a"), str)
    assert isinstance(loader.parse("---\nname: a\n---\nbody\n", "a"), str)


def test_an_unknown_key_is_a_problem() -> None:
    text = "---\nname: a\ndescription: d\nmodel: gpt\n---\nbody\n"
    problem = loader.parse(text, "a")
    assert isinstance(problem, str)
    assert "Unknown frontmatter key" in problem


def test_the_allowlist_never_widens() -> None:
    assert tools.allowed(["write_file", "delete", "run_command"]) == []
    assert tools.allowed([]) == sorted({"ls", "read_file", "glob", "grep"})
    assert tools.rejected(["write_file", "grep"]) == ["write_file"]


def test_discovery_lists_files_and_reports_broken_ones(workspace: Path) -> None:
    write(workspace, "api-reviewer", TEXT)
    write(workspace, "broken", "---\nname: broken\n---\n")
    found = {record.name: record for record in loader.discover(workspace)}
    assert found["api-reviewer"].problem is None
    assert found["broken"].problem
    assert found["api-reviewer"].path == ".harness/agents/api-reviewer.md"


def test_a_symlinked_file_is_skipped(workspace: Path) -> None:
    write(workspace, "api-reviewer", TEXT)
    target = storage_path(workspace, "agents/api-reviewer.md")
    link = storage_path(workspace, "agents/linked.md")
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks need a privilege this host does not grant")
    assert [record.name for record in loader.discover(workspace)] == ["api-reviewer"]


def test_a_traversal_name_reads_nothing(workspace: Path) -> None:
    assert loader.read(workspace, "../secrets") is None
    assert loader.read(workspace, "UPPER") is None


def test_render_round_trips(workspace: Path) -> None:
    text = loader.render("api-reviewer", "Reviews the HTTP layer.", "Look closely.", ["grep"])
    parsed = loader.parse(text, "api-reviewer")
    assert not isinstance(parsed, str)
    record, instructions = parsed
    assert record.tools == ["grep"]
    assert instructions == "Look closely."


def test_the_route_lists_and_reads(workspace: Path) -> None:
    write(workspace, "api-reviewer", TEXT)
    with client() as http:
        listed = http.get("/agents", headers=HEADERS, params={"workspace": str(workspace)})
        detail = http.get(
            "/agents/api-reviewer", headers=HEADERS, params={"workspace": str(workspace)}
        )
        missing = http.get("/agents/ghost", headers=HEADERS, params={"workspace": str(workspace)})
    assert [item["name"] for item in listed.json()] == ["api-reviewer"]
    assert "report drift" in detail.json()["instructions"]
    assert missing.status_code == 404


def test_creating_is_a_proposal_and_approving_writes_it(workspace: Path) -> None:
    with client() as http:
        response = http.post(
            "/agents",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={
                "name": "doc-checker",
                "description": "Checks docs against code.",
                "instructions": "Compare each claim with the source.",
                "tools": ["read_file", "delete"],
            },
        )
        assert response.status_code == 202, response.text
        assert not storage_path(workspace, "agents/doc-checker.md").exists()
        record = response.json()
        assert record["request"]["tool"] == "agent_create"
        assert "doc-checker" in record["request"]["diff"]
        approve(http, record)
    text = storage_path(workspace, "agents/doc-checker.md").read_text(encoding="utf-8")
    assert "Compare each claim" in text
    assert "tools: read_file" in text
    assert "delete" not in text


def test_a_duplicate_create_is_refused(workspace: Path) -> None:
    write(workspace, "api-reviewer", TEXT)
    with client() as http:
        response = http.post(
            "/agents",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"name": "api-reviewer", "description": "x", "instructions": "y"},
        )
    assert response.status_code == 409


def test_editing_requires_the_existing_file(workspace: Path) -> None:
    write(workspace, "api-reviewer", TEXT)
    with client() as http:
        edited = http.put(
            "/agents/api-reviewer",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={
                "name": "api-reviewer",
                "description": "Reviews the HTTP layer.",
                "instructions": "Now also check status codes.",
            },
        )
        assert edited.status_code == 202, edited.text
        approve(http, edited.json())
        missing = http.put(
            "/agents/ghost",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"name": "ghost", "description": "x", "instructions": "y"},
        )
        mismatch = http.put(
            "/agents/api-reviewer",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"name": "other", "description": "x", "instructions": "y"},
        )
    assert "status codes" in storage_path(workspace, "agents/api-reviewer.md").read_text()
    assert missing.status_code == 409
    assert mismatch.status_code == 400


def test_deleting_removes_the_file(workspace: Path) -> None:
    write(workspace, "api-reviewer", TEXT)
    with client() as http:
        response = http.delete(
            "/agents/api-reviewer", headers=HEADERS, params={"workspace": str(workspace)}
        )
        assert response.status_code == 202
        assert response.json()["request"]["tool"] == "agent_delete"
        approve(http, response.json())
        again = http.delete(
            "/agents/api-reviewer", headers=HEADERS, params={"workspace": str(workspace)}
        )
    assert not storage_path(workspace, "agents/api-reviewer.md").exists()
    assert again.status_code == 409
