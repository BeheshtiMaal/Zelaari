"""Workspace verification settings: defaults, bounds, approval, atomicity."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from tools.jail import storage_path
from tools.snapshot import SnapshotError, SnapshotStore
from verify.settings import ContextSettings, VerifyConfig, load_config

HEADERS = {"Authorization": "Bearer token"}


def config_path(root: Path) -> Path:
    directory = storage_path(root, "")
    directory.mkdir(exist_ok=True)
    return storage_path(root, "config.json")


def test_defaults_match_the_mock(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.context.model_dump() == {
        "compaction_percent": 60,
        "keep_messages": 8,
        "offload": True,
        "show_ring": True,
    }
    assert config.verify.model_dump() == {
        "gate": True,
        "command": None,
        "max_steps": 40,
        "max_minutes": 30,
        "fix_attempts": 3,
    }
    assert config.terminal.model_dump() == {
        "shell": "auto",
        "timeout_seconds": 120,
        "max_output_lines": 200,
    }


def test_corrupt_config_yields_defaults_without_raising(tmp_path: Path) -> None:
    target = config_path(tmp_path)
    target.write_text("{broken", encoding="utf-8")
    assert load_config(tmp_path) == VerifyConfig()
    target.write_text('{"context": {"compaction_percent": 500}}', encoding="utf-8")
    config = load_config(tmp_path)
    assert config.context.compaction_percent == 60


def test_partial_sections_keep_the_rest_of_the_document(tmp_path: Path) -> None:
    target = config_path(tmp_path)
    target.write_text(
        json.dumps({"planning": {"step_threshold": 5}, "other": {"kept": True}}), encoding="utf-8"
    )
    with TestClient(create_app("token")) as http:
        params = {"workspace": str(tmp_path)}
        assert http.get("/verify/settings", params=params).status_code == 401
        body = http.get("/verify/settings", headers=HEADERS, params=params).json()
        assert body["context"]["compaction_percent"] == 60
        assert body["detection"] == {"command": None, "source": "none"}
        proposal = http.put(
            "/verify/settings",
            headers=HEADERS,
            params=params,
            json={
                "context": {
                    "compaction_percent": 45,
                    "keep_messages": 4,
                    "offload": False,
                    "show_ring": False,
                },
                "verify": {
                    "gate": False,
                    "command": "pytest -x",
                    "max_steps": 12,
                    "max_minutes": 5,
                    "fix_attempts": 1,
                },
                "terminal": {"shell": "cmd", "timeout_seconds": 30, "max_output_lines": 500},
            },
        )
        assert proposal.status_code == 202, proposal.text
        # Nothing is written before the person approves.
        assert json.loads(target.read_text(encoding="utf-8")) == {
            "planning": {"step_threshold": 5},
            "other": {"kept": True},
        }
        request = proposal.json()["request"]
        assert request["path"] == ".harness/config.json"
        assert request["diff"]
        decision = http.post(
            f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
            headers=HEADERS,
            json={"decision": "approve", "revision": request["revision"]},
        )
        assert decision.status_code == 200, decision.text
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["planning"] == {"step_threshold": 5}
    assert saved["other"] == {"kept": True}
    assert saved["context"]["compaction_percent"] == 45
    assert saved["verify"]["command"] == "pytest -x"
    assert saved["terminal"]["shell"] == "cmd"
    snapshots = SnapshotStore(tmp_path)
    snapshot = next(entry for entry in snapshots.entries() if entry.path == ".harness/config.json")
    assert b'"step_threshold": 5' in (snapshots.content(snapshot.id) or b"")
    with pytest.raises(SnapshotError):
        snapshots.revert(snapshot.id)


@pytest.mark.parametrize(
    "section,value",
    [
        ("context", {"compaction_percent": 29}),
        ("context", {"compaction_percent": 91}),
        ("context", {"keep_messages": 51}),
        ("context", {"offload": "yes"}),
        ("verify", {"max_steps": 0}),
        ("verify", {"max_steps": 201}),
        ("verify", {"max_minutes": 0}),
        ("verify", {"fix_attempts": 11}),
        ("verify", {"command": "x" * 401}),
        ("terminal", {"shell": "bash"}),
        ("terminal", {"timeout_seconds": 0}),
        ("terminal", {"timeout_seconds": 601}),
        ("terminal", {"max_output_lines": 19}),
        ("terminal", {"max_output_lines": 2001}),
    ],
)
def test_out_of_range_values_are_rejected_without_writing(
    tmp_path: Path, section: str, value: dict[str, object]
) -> None:
    target = config_path(tmp_path)
    target.write_text('{"verify": {"max_steps": 7}}', encoding="utf-8")
    body = VerifyConfig().model_dump(mode="json")
    body[section].update(value)
    with TestClient(create_app("token")) as http:
        response = http.put(
            "/verify/settings", headers=HEADERS, params={"workspace": str(tmp_path)}, json=body
        )
        assert response.status_code == 422, response.text
    assert json.loads(target.read_text(encoding="utf-8")) == {"verify": {"max_steps": 7}}


def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    config_path(tmp_path).write_text("{}", encoding="utf-8")
    body = VerifyConfig().model_dump(mode="json")
    body["terminal"]["extra"] = 1
    with TestClient(create_app("token")) as http:
        response = http.put(
            "/verify/settings", headers=HEADERS, params={"workspace": str(tmp_path)}, json=body
        )
        assert response.status_code == 422


def test_blank_command_means_auto(tmp_path: Path) -> None:
    assert ContextSettings().keep_messages == 8
    config = VerifyConfig.model_validate(
        {"verify": {"command": "   ", "max_steps": 40, "max_minutes": 30, "fix_attempts": 3}}
    )
    assert config.verify.command is None


def test_detection_is_reported_for_the_selected_workspace(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\ndependencies = ['pytest>=8']\n", encoding="utf-8"
    )
    with TestClient(create_app("token")) as http:
        body = http.get(
            "/verify/settings", headers=HEADERS, params={"workspace": str(tmp_path)}
        ).json()
    assert body["detection"] == {"command": "pytest -q", "source": "pyproject.toml"}


def test_custom_command_overrides_detection(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    config_path(tmp_path).write_text(
        json.dumps(
            {
                "verify": {
                    "command": "pytest -x -q",
                    "max_steps": 40,
                    "max_minutes": 30,
                    "fix_attempts": 3,
                }
            }
        ),
        encoding="utf-8",
    )
    with TestClient(create_app("token")) as http:
        body = http.get(
            "/verify/settings", headers=HEADERS, params={"workspace": str(tmp_path)}
        ).json()
    assert body["detection"] == {"command": "pytest -x -q", "source": "custom"}


def test_invalid_workspace_is_rejected(tmp_path: Path) -> None:
    with TestClient(create_app("token")) as http:
        assert (
            http.get("/verify/settings", headers=HEADERS, params={"workspace": "C:\\"}).status_code
            == 400
        )
