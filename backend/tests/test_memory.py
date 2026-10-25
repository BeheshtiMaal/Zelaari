"""Workspace memory: one bounded file, read at run start, written through approval."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agents import memory
from server.app import create_app
from tools.jail import storage_path

HEADERS = {"Authorization": "Bearer token"}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".harness").mkdir()
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


def test_an_empty_workspace_has_no_block(workspace: Path) -> None:
    assert memory.load(workspace).content == ""
    assert memory.block(workspace) == ""


def test_the_file_is_read_and_bounded(workspace: Path) -> None:
    storage_path(workspace, "memory.md").write_text("Use ruff.\n", encoding="utf-8")
    document = memory.load(workspace)
    assert document.content == "Use ruff.\n"
    assert document.bytes == len(b"Use ruff.\n")
    assert "Use ruff." in memory.block(workspace)
    assert memory.block(workspace).startswith("Workspace memory")


def test_the_block_is_capped(workspace: Path) -> None:
    storage_path(workspace, "memory.md").write_text("x" * 9000, encoding="utf-8")
    block = memory.block(workspace)
    assert len(block) < 9000
    assert block.endswith("…")


def test_an_oversized_file_is_not_read(workspace: Path) -> None:
    storage_path(workspace, "memory.md").write_text("x" * (memory.LIMIT + 10), encoding="utf-8")
    document = memory.load(workspace)
    assert document.content == ""
    assert document.bytes > memory.LIMIT


def test_the_route_reads(workspace: Path) -> None:
    storage_path(workspace, "memory.md").write_text("Persian notes", encoding="utf-8")
    with client() as http:
        response = http.get("/memory", headers=HEADERS, params={"workspace": str(workspace)})
    assert response.status_code == 200
    assert response.json()["content"] == "Persian notes"
    assert response.json()["limit"] == memory.LIMIT


def test_writing_is_a_proposal_and_approving_writes_it(workspace: Path) -> None:
    with client() as http:
        response = http.put(
            "/memory",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"content": "Always run the gates before a commit.\n"},
        )
        assert response.status_code == 202, response.text
        assert not storage_path(workspace, "memory.md").exists()
        record = response.json()
        assert record["request"]["tool"] == "memory_update"
        assert "gates" in record["request"]["diff"]
        approve(http, record)
    assert "gates" in storage_path(workspace, "memory.md").read_text(encoding="utf-8")


def test_rejecting_writes_nothing(workspace: Path) -> None:
    with client() as http:
        response = http.put(
            "/memory",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"content": "nope"},
        )
        request = response.json()["request"]
        http.post(
            f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
            headers=HEADERS,
            json={"decision": "reject", "reason": "no"},
        )
    assert not storage_path(workspace, "memory.md").exists()


def test_an_edit_is_a_new_revision_not_a_replacement(workspace: Path) -> None:
    storage_path(workspace, "memory.md").write_text("first\n", encoding="utf-8")
    with client() as http:
        response = http.put(
            "/memory",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"content": "second\n"},
        )
        assert response.status_code == 202
        diff = response.json()["request"]["diff"]
        assert "-first" in diff and "+second" in diff
        approve(http, response.json())
    assert storage_path(workspace, "memory.md").read_text(encoding="utf-8") == "second\n"
