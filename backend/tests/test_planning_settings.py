"""Authenticated, always-reviewed workspace planning configuration."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from permissions.types import ApprovalDecision
from planning.policy import load_settings
from planning.types import PlanningSettings
from server.app import create_app
from store.actions import ActionApprovals
from store.catalog import Catalog
from tools.jail import storage_path
from tools.snapshot import SnapshotError, SnapshotStore

HEADERS = {"Authorization": "Bearer token"}


def test_authenticated_settings_save_asks_even_auto_and_preserves_keys(tmp_path: Path) -> None:
    directory = storage_path(tmp_path, "")
    directory.mkdir()
    storage_path(tmp_path, "rules.json").write_text('{"mode":"auto"}', encoding="utf-8")
    target = storage_path(tmp_path, "config.json")
    target.write_text('{"other": {"preserved": true}}', encoding="utf-8")
    with TestClient(create_app("token")) as http:
        params = {"workspace": str(tmp_path)}
        assert http.get("/planning/settings", params=params).status_code == 401
        assert http.get("/planning/settings", headers=HEADERS, params=params).json() == {
            "plan_gate": True,
            "step_threshold": 4,
            "file_threshold": 3,
            "deviation_gate": True,
        }
        proposal = http.put(
            "/planning/settings",
            headers=HEADERS,
            params=params,
            json={"step_threshold": 5, "file_threshold": 6, "deviation_gate": False},
        )
        assert proposal.status_code == 202, proposal.text
        assert "planning" not in json.loads(target.read_text(encoding="utf-8"))
        request = proposal.json()["request"]
        assert request["diff"]
        decision = http.post(
            f"/runs/{request['run_id']}/interrupts/{request['approval_id']}",
            headers=HEADERS,
            json={"decision": "approve", "revision": request["revision"]},
        )
        assert decision.status_code == 200, decision.text
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "other": {"preserved": True},
        "planning": {
            "plan_gate": True,
            "step_threshold": 5,
            "file_threshold": 6,
            "deviation_gate": False,
        },
    }
    snapshots = SnapshotStore(tmp_path)
    snapshot = next(entry for entry in snapshots.entries() if entry.path == ".harness/config.json")
    assert snapshots.content(snapshot.id) == b'{"other": {"preserved": true}}'
    with pytest.raises(SnapshotError):
        snapshots.revert(snapshot.id)


def test_reject_stale_and_reconstruction(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "profile.json")
    root = tmp_path / "workspace"
    root.mkdir()
    actions = ActionApprovals(catalog)
    proposal = actions.propose_planning(root, PlanningSettings(step_threshold=5))
    # Independent action ledger instance sees the durable pending proposal.
    restored = ActionApprovals(catalog)
    restored.resolve(
        proposal.request.run_id,
        proposal.request.approval_id,
        ApprovalDecision(decision="reject", reason="Keep defaults"),
    )
    assert not storage_path(root, "config.json").exists()
    proposal = actions.propose_planning(root, PlanningSettings(step_threshold=6))
    storage_path(root, "config.json").write_text('{"external": true}', encoding="utf-8")
    with pytest.raises(ValueError):
        restored.resolve(
            proposal.request.run_id,
            proposal.request.approval_id,
            ApprovalDecision(decision="approve"),
        )
    assert load_settings(root)[0] == PlanningSettings()


@pytest.mark.parametrize("raw", ["{broken", "[]", '{"planning":{"file_threshold":0}}'])
def test_malformed_configuration_never_overwritten(tmp_path: Path, raw: str) -> None:
    directory = storage_path(tmp_path, "")
    directory.mkdir()
    target = storage_path(tmp_path, "config.json")
    target.write_text(raw, encoding="utf-8")
    with TestClient(create_app("token")) as http:
        response = http.put(
            "/planning/settings", headers=HEADERS, params={"workspace": str(tmp_path)}, json={}
        )
        assert response.status_code == 409
    assert target.read_text(encoding="utf-8") == raw
