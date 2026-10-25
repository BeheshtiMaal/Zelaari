"""What the Data card reports, and what clearing it is allowed to remove."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from appdata.retention import clear, prune, run_directories
from appdata.types import DataSummary
from providers.base import TaskRecord, Workspace, WorkspaceState
from server.app import create_app
from store.catalog import Catalog

HEADERS = {"Authorization": "Bearer token"}


def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('keep me')\n", encoding="utf-8")
    runs = root / ".harness" / "runs"
    (runs / "run-1").mkdir(parents=True)
    (runs / "run-1" / "events.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    (runs / "run-2").mkdir(parents=True)
    (runs / "run-2" / "events.jsonl").write_text("{}\n", encoding="utf-8")
    (root / ".harness" / "checkpoints.sqlite").write_bytes(b"x" * 32)
    (root / ".harness" / "rules.json").write_text('{"mode":"ask"}', encoding="utf-8")
    return root


def catalog_with(root: Path, tmp_path: Path) -> Catalog:
    catalog = Catalog(tmp_path / "profile.json")
    catalog.data.workspaces = WorkspaceState(
        recent=[Workspace(path=str(root), name=root.name)],
        selected=str(root),
        tasks=[
            TaskRecord(id="run-1", workspace=str(root), title="First", model="demo"),
            TaskRecord(id="run-9", workspace="C:/elsewhere", title="Other", model="demo"),
        ],
    )
    return catalog


def test_the_summary_counts_without_leaking_paths(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    catalog = catalog_with(root, tmp_path)
    with TestClient(create_app("token", catalog=catalog, app_data=tmp_path / "app")) as client:
        response = client.get("/data", headers=HEADERS)
        assert response.status_code == 200
        body = DataSummary.model_validate(response.json())
    assert body.app_data == str(tmp_path / "app")
    assert body.retention_days == 30
    assert body.keys == 0
    assert len(body.workspaces) == 1
    item = body.workspaces[0]
    assert item.path == str(root)
    assert item.harness == str(root / ".harness")
    assert item.runs == 2
    assert item.tasks == 1
    assert item.checkpoints_bytes == 32
    events = (root / ".harness" / "runs").glob("*/events.jsonl")
    assert item.run_bytes == sum(path.stat().st_size for path in events)
    # A count is a count: the run ids and their event text stay out of the payload.
    assert "run-1" not in response.text
    assert "events.jsonl" not in response.text


def test_an_unknown_workspace_is_rejected_but_a_stale_one_is_skipped(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    catalog = catalog_with(root, tmp_path)
    catalog.data.workspaces.recent.append(Workspace(path=str(tmp_path / "gone"), name="gone"))
    with TestClient(create_app("token", catalog=catalog, app_data=tmp_path / "app")) as client:
        missing = client.get("/data", headers=HEADERS, params={"workspace": str(tmp_path / "nope")})
        assert missing.status_code == 400
        body = client.get("/data", headers=HEADERS).json()
    assert [item["path"] for item in body["workspaces"]] == [str(root)]


def test_clearing_removes_run_storage_and_never_a_workspace_file(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    catalog = catalog_with(root, tmp_path)
    with TestClient(create_app("token", catalog=catalog, app_data=tmp_path / "app")) as client:
        response = client.delete("/data/runs", headers=HEADERS, params={"workspace": str(root)})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["runs"] == 2
        assert body["tasks"] == 1
        assert body["bytes"] > 0
    assert not (root / ".harness" / "runs" / "run-1").exists()
    assert not (root / ".harness" / "runs" / "run-2").exists()
    assert not (root / ".harness" / "checkpoints.sqlite").exists()
    # Engine storage that is not history, and the project itself, survive untouched.
    assert (root / ".harness" / "rules.json").is_file()
    assert (root / "src" / "app.py").read_text(encoding="utf-8") == "print('keep me')\n"
    # Only this workspace's task rows are gone.
    assert [task.id for task in catalog.data.workspaces.tasks] == ["run-9"]
    assert json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))["workspaces"][
        "tasks"
    ][0]["id"] == "run-9"


def test_clearing_is_refused_while_a_run_is_working(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    catalog = catalog_with(root, tmp_path)

    class Busy:
        def busy(self) -> bool:
            return True

        async def close(self) -> None:
            return None

    with TestClient(create_app("token", service=Busy(), catalog=catalog)) as client:  # type: ignore[arg-type]
        response = client.delete("/data/runs", headers=HEADERS, params={"workspace": str(root)})
        assert response.status_code == 409
    assert (root / ".harness" / "runs" / "run-1").is_dir()


def test_retention_keeps_the_window_and_zero_keeps_everything(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    old = root / ".harness" / "runs" / "run-1"
    old_time = (datetime.now(UTC) - timedelta(days=45)).timestamp()
    os.utime(old, (old_time, old_time))
    assert prune(root, 0) == 0
    assert len(run_directories(root)) == 2
    assert prune(root, 30) == 1
    assert [path.name for path in run_directories(root)] == ["run-2"]
    assert (root / "src" / "app.py").is_file()
    # A second pass has nothing left to remove.
    assert prune(root, 30) == 0


def test_the_run_list_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = workspace(tmp_path)
    for index in range(5):
        (root / ".harness" / "runs" / f"extra-{index}").mkdir()
    monkeypatch.setattr("appdata.retention.MAX_RUNS_PER_CALL", 3)
    assert len(run_directories(root)) == 3
    removed, _ = clear(root)
    assert removed == 3
    # Seven folders existed; one call removed three of them and left the rest for the next call.
    assert len(list((root / ".harness" / "runs").iterdir())) == 4


def test_clearing_a_workspace_with_no_history_is_not_an_error(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert clear(root) == (0, 0)
    assert run_directories(root) == []
