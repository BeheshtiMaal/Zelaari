"""The files a run changed, derived from its snapshots and never from the model's words."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.snapshots import changed_files
from tools.jail import resolve
from tools.snapshot import SnapshotStore

HEADERS = {"Authorization": "Bearer token"}


def capture(root: Path, relative: str, *, run_id: str, tool: str = "write_file") -> None:
    store = SnapshotStore(root, run_id=run_id)
    store.capture(resolve(root, relative), tool=tool)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / ".harness").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('old')\n", encoding="utf-8")
    return tmp_path


def test_a_run_sees_only_its_own_paths(workspace: Path) -> None:
    capture(workspace, "src/main.py", run_id="run-1")
    capture(workspace, "README.md", run_id="run-2")
    files = changed_files(workspace, "run-1")
    assert [file.path for file in files] == ["src/main.py"]
    assert files[0].created is False
    assert files[0].tool == "write_file"


def test_a_created_file_is_marked_and_the_list_is_sorted(workspace: Path) -> None:
    capture(workspace, "src/main.py", run_id="run-1")
    (workspace / "docs").mkdir()
    capture(workspace, "docs/notes.md", run_id="run-1")
    files = changed_files(workspace, "run-1")
    assert [file.path for file in files] == ["docs/notes.md", "src/main.py"]
    assert [file.created for file in files] == [True, False]


def test_a_path_captured_twice_appears_once_with_its_latest_state(workspace: Path) -> None:
    capture(workspace, "src/main.py", run_id="run-1")
    (workspace / "src" / "main.py").write_text("print('new')\n", encoding="utf-8")
    capture(workspace, "src/main.py", run_id="run-1", tool="apply_patch")
    files = changed_files(workspace, "run-1")
    assert len(files) == 1
    assert files[0].tool == "apply_patch"


def test_an_unknown_run_is_a_404_and_a_known_one_lists_its_files(workspace: Path) -> None:
    http = TestClient(create_app("token"))
    assert http.get("/runs/run-1/files", headers=HEADERS).status_code == 404
    capture(workspace, "src/main.py", run_id="run-1")
    # A workspace that was never selected cannot be read back, and says so instead of guessing.
    assert http.get("/runs/run-1/files", headers=HEADERS).status_code == 404
