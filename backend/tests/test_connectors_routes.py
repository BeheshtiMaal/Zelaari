"""Connector routes: reads are direct, every write is a reviewed capability grant."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from connectors.config import McpFile
from server.app import create_app
from tools.jail import storage_path

HEADERS = {"Authorization": "Bearer token"}
WORKER = Path(__file__).with_name("mcp_worker.py")


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


def reject(http: TestClient, record: dict[str, object]) -> None:
    request = record["request"]
    assert isinstance(request, dict)
    response = http.post(
        f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
        headers=HEADERS,
        json={"decision": "reject", "reason": "no"},
    )
    assert response.status_code == 200, response.text


def stored(workspace: Path) -> list[str]:
    path = storage_path(workspace, "mcp.json")
    if not path.is_file():
        return []
    return [server.name for server in McpFile.model_validate_json(path.read_text()).servers]


def body(name: str = "fixture", mode: str = "normal") -> dict[str, object]:
    return {
        "name": name,
        "transport": "stdio",
        "command": f'"{sys.executable}" "{WORKER}" {mode}',
        "env_keys": [],
        "enabled": True,
    }


def test_an_empty_workspace_lists_nothing(workspace: Path) -> None:
    with client() as http:
        response = http.get("/connectors", headers=HEADERS, params={"workspace": str(workspace)})
    assert response.status_code == 200
    body = response.json()
    assert Path(body["workspace"]) == workspace
    assert body["servers"] == []


def test_adding_a_server_is_a_proposal_and_approving_writes_it(workspace: Path) -> None:
    with client() as http:
        response = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json=body(),
        )
        assert response.status_code == 202, response.text
        assert stored(workspace) == []
        record = response.json()
        assert record["request"]["tool"] == "mcp_server_add"
        assert record["request"]["path"] == ".harness/mcp.json"
        assert "fixture" in record["request"]["diff"]
        approve(http, record)
    assert stored(workspace) == ["fixture"]
    text = storage_path(workspace, "mcp.json").read_text(encoding="utf-8")
    assert "mcp_worker.py" in text


def test_rejecting_an_add_writes_nothing(workspace: Path) -> None:
    with client() as http:
        response = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json=body(),
        )
        reject(http, response.json())
    assert stored(workspace) == []


def test_a_duplicate_name_is_refused(workspace: Path) -> None:
    with client() as http:
        first = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
        approve(http, first.json())
        second = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
    assert second.status_code == 409


def test_a_command_that_cannot_parse_is_refused(workspace: Path) -> None:
    with client() as http:
        response = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={**body(), "command": 'node "unbalanced'},
        )
    assert response.status_code == 409
    assert "unbalanced" in response.json()["detail"]


def test_an_http_server_needs_https(workspace: Path) -> None:
    with client() as http:
        response = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={"name": "remote", "transport": "http", "url": "http://x.test/mcp"},
        )
    assert response.status_code == 409
    assert "https" in response.json()["detail"]


def test_a_listed_server_reports_its_tools(workspace: Path) -> None:
    with client() as http:
        added = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
        approve(http, added.json())
        listed = http.get(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}
        ).json()
    server = listed["servers"][0]
    assert server["status"] == "connected"
    assert [tool["namespaced"] for tool in server["tools"]] == [
        "fixture__echo",
        "fixture__count",
    ]


def test_a_server_that_cannot_start_is_a_card(workspace: Path) -> None:
    with client() as http:
        added = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={**body(), "command": "definitely-not-installed-binary"},
        )
        approve(http, added.json())
        listed = http.get(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}
        ).json()
    assert listed["servers"][0]["status"] == "error"
    assert listed["servers"][0]["error"]


def test_a_disabled_server_is_not_started(workspace: Path) -> None:
    with client() as http:
        added = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={**body(), "command": "definitely-not-installed-binary", "enabled": False},
        )
        approve(http, added.json())
        listed = http.get(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}
        ).json()
    assert listed["servers"][0]["status"] == "disabled"
    assert listed["servers"][0]["enabled"] is False


def test_update_replaces_one_server_and_keeps_the_rest(workspace: Path) -> None:
    with client() as http:
        first = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
        approve(http, first.json())
        second = http.post(
            "/connectors",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json=body("second"),
        )
        approve(http, second.json())
        updated = http.put(
            "/connectors/fixture",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json={**body(), "enabled": False},
        )
        assert updated.status_code == 202, updated.text
        assert updated.json()["request"]["tool"] == "mcp_server_update"
        approve(http, updated.json())
        listed = http.get(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}
        ).json()
    assert [item["name"] for item in listed["servers"]] == ["fixture", "second"]
    assert listed["servers"][0]["enabled"] is False
    assert listed["servers"][1]["enabled"] is True


def test_updating_an_unknown_server_is_404(workspace: Path) -> None:
    with client() as http:
        response = http.put(
            "/connectors/ghost",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json=body("ghost"),
        )
    assert response.status_code == 404


def test_a_path_and_body_name_mismatch_is_refused(workspace: Path) -> None:
    with client() as http:
        response = http.put(
            "/connectors/fixture",
            headers=HEADERS,
            params={"workspace": str(workspace)},
            json=body("other"),
        )
    assert response.status_code == 400


def test_deleting_removes_the_entry(workspace: Path) -> None:
    with client() as http:
        added = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
        approve(http, added.json())
        deleted = http.delete(
            "/connectors/fixture", headers=HEADERS, params={"workspace": str(workspace)}
        )
        assert deleted.status_code == 202
        assert deleted.json()["request"]["tool"] == "mcp_server_delete"
        approve(http, deleted.json())
        missing = http.delete(
            "/connectors/fixture", headers=HEADERS, params={"workspace": str(workspace)}
        )
    assert stored(workspace) == []
    assert missing.status_code == 404


def test_test_only_runs_a_stored_server(workspace: Path) -> None:
    with client() as http:
        unknown = http.post(
            "/connectors/ghost/test", headers=HEADERS, params={"workspace": str(workspace)}
        )
        added = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
        pending = http.post(
            "/connectors/fixture/test", headers=HEADERS, params={"workspace": str(workspace)}
        )
        approve(http, added.json())
        tested = http.post(
            "/connectors/fixture/test", headers=HEADERS, params={"workspace": str(workspace)}
        )
    assert unknown.status_code == 404
    assert pending.status_code == 404
    assert tested.status_code == 200
    assert tested.json()["status"] == "connected"


def test_the_written_file_is_exactly_what_was_reviewed(workspace: Path) -> None:
    path = storage_path(workspace, "mcp.json")
    path.write_text(json.dumps({"version": 1, "servers": [], "note": "stale"}), encoding="utf-8")
    with client() as http:
        added = http.post(
            "/connectors", headers=HEADERS, params={"workspace": str(workspace)}, json=body()
        )
        approve(http, added.json())
    document = json.loads(path.read_text(encoding="utf-8"))
    assert "note" not in document
    assert [server["name"] for server in document["servers"]] == ["fixture"]
