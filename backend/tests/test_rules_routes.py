"""R18: the rules grid is readable and writable through the engine, and it round-trips."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.app import create_app
from tools.jail import storage_path

HEADERS = {"Authorization": "Bearer token"}


def client() -> TestClient:
    return TestClient(create_app("token"))


def test_a_fresh_workspace_reports_the_ask_defaults(tmp_path: Path) -> None:
    with client() as http:
        response = http.get("/rules", headers=HEADERS, params={"workspace": str(tmp_path)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "ask"
    assert body["tools"] == {}
    assert body["defaults"]["write"] == "ask"
    assert body["defaults"]["read"] == "allow"
    assert "high-risk commands" in body["always_ask"]


def test_a_saved_grid_round_trips(tmp_path: Path) -> None:
    payload = {
        "version": 1,
        "mode": "auto",
        "tools": {"write_file": [{"glob": "src/**", "action": "allow"}]},
    }
    with client() as http:
        saved = http.put(
            "/rules", headers=HEADERS, params={"workspace": str(tmp_path)}, json=payload
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["tools"] == {"write_file": [{"glob": "src/**", "action": "allow"}]}

        reread = http.get("/rules", headers=HEADERS, params={"workspace": str(tmp_path)})
    assert reread.json() == saved.json()
    assert reread.json()["mode"] == "auto"
    assert reread.json()["defaults"]["write"] == "allow"


def test_the_grid_lands_in_engine_storage(tmp_path: Path) -> None:
    with client() as http:
        http.put(
            "/rules",
            headers=HEADERS,
            params={"workspace": str(tmp_path)},
            json={"tools": {"run_command": [{"glob": "*", "action": "deny"}]}},
        )
    written = json.loads(storage_path(tmp_path, "rules.json").read_text(encoding="utf-8"))
    assert written["tools"]["run_command"][0]["action"] == "deny"


def test_an_unknown_action_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    with client() as http:
        response = http.put(
            "/rules",
            headers=HEADERS,
            params={"workspace": str(tmp_path)},
            json={"tools": {"write_file": [{"glob": "*", "action": "maybe"}]}},
        )
    assert response.status_code == 422
    assert not storage_path(tmp_path, "rules.json").exists()


def test_a_traversal_glob_is_refused(tmp_path: Path) -> None:
    with client() as http:
        response = http.put(
            "/rules",
            headers=HEADERS,
            params={"workspace": str(tmp_path)},
            json={"tools": {"write_file": [{"glob": "../**", "action": "allow"}]}},
        )
    assert response.status_code == 422


def test_a_malformed_file_still_answers_and_asks(tmp_path: Path) -> None:
    """Fail closed: an unreadable grid must not read back as 'everything allowed'."""
    target = storage_path(tmp_path, "rules.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{ not json", encoding="utf-8")
    with client() as http:
        response = http.get("/rules", headers=HEADERS, params={"workspace": str(tmp_path)})
    assert response.status_code == 200
    assert response.json()["mode"] == "ask"


def test_a_bad_workspace_is_rejected(tmp_path: Path) -> None:
    with client() as http:
        response = http.get(
            "/rules", headers=HEADERS, params={"workspace": str(tmp_path / "absent")}
        )
    assert response.status_code == 400
