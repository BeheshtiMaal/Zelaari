"""Snapshot capture, revert and retention. Revert must restore exact bytes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from store.secrets import Redactor
from tools.fs import WorkspaceBackend
from tools.jail import resolve
from tools.snapshot import SnapshotError, SnapshotStore


@pytest.fixture()
def setup(tmp_path: Path) -> tuple[Path, SnapshotStore, WorkspaceBackend]:
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.txt").write_bytes(b"first\n")
    store = SnapshotStore(root, run_id="run-1")
    return root, store, WorkspaceBackend(root, Redactor(), store)


def test_create_write_edit_delete_each_snapshot_the_previous_state(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, store, backend = setup

    assert backend.write("src/new.txt", "one").error is None
    created = store.newest_for("src/new.txt")
    assert created is not None and created.existed is False

    assert backend.write("src/new.txt", "two").error is None
    overwritten = store.newest_for("src/new.txt")
    assert overwritten is not None and overwritten.existed is True
    assert (store.directory / overwritten.id / "content.bin").read_bytes() == b"one"

    assert backend.edit("src/a.txt", "first", "second").error is None
    edited = store.newest_for("src/a.txt")
    assert edited is not None and edited.tool == "edit_file"
    assert (store.directory / edited.id / "content.bin").read_bytes() == b"first\n"

    assert backend.delete("src/new.txt").error is None
    deleted = store.newest_for("src/new.txt")
    assert deleted is not None and deleted.tool == "delete"
    assert (store.directory / deleted.id / "content.bin").read_bytes() == b"two"
    assert (root / "src" / "a.txt").read_text(encoding="utf-8") == "second\n"


def test_revert_restores_exact_bytes(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, store, backend = setup
    backend.write("src/a.txt", "second\n")
    target = store.newest_for("src/a.txt")
    assert target is not None

    result = store.revert(target.id)
    assert (root / "src" / "a.txt").read_bytes() == b"first\n"
    assert result.path == "src/a.txt"
    assert store.meta(result.created_snapshot_id).tool == "revert"


def test_revert_of_a_created_file_deletes_it(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, store, backend = setup
    backend.write("src/brand-new.txt", "content")
    created = store.newest_for("src/brand-new.txt")
    assert created is not None and created.existed is False

    store.revert(created.id)
    assert not (root / "src" / "brand-new.txt").exists()


def test_a_revert_is_itself_revertible(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, store, backend = setup
    backend.write("src/a.txt", "second\n")
    first = store.newest_for("src/a.txt")
    assert first is not None
    outcome = store.revert(first.id)
    assert (root / "src" / "a.txt").read_text(encoding="utf-8") == "first\n"

    store.revert(outcome.created_snapshot_id)
    assert (root / "src" / "a.txt").read_text(encoding="utf-8") == "second\n"


def test_pruning_keeps_the_newest_and_respects_the_budget(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "a.txt").write_text("x" * 100, encoding="utf-8")
    store = SnapshotStore(root, max_entries=3, max_bytes=10_000_000)
    target = resolve(root, "a.txt")
    for _ in range(6):
        store.capture(target, tool="write_file")

    entries = store.entries()
    assert len(entries) == 3
    assert [entry.id for entry in entries] == sorted((entry.id for entry in entries), reverse=True)


def test_prune_never_removes_the_entry_in_use(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "a.txt").write_text("x", encoding="utf-8")
    store = SnapshotStore(root, max_entries=1, max_bytes=10_000_000)
    target = resolve(root, "a.txt")
    first = store.capture(target, tool="write_file")
    store.prune(keep=first)
    assert any(entry.id == first for entry in store.entries())


def test_snapshot_failure_aborts_the_mutation(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, _store, backend = setup
    original = (root / "src" / "a.txt").read_bytes()

    def explode(*_args: object, **_kwargs: object) -> str:
        raise SnapshotError("disk full")

    assert backend.snapshots is not None
    backend.snapshots.capture = explode  # type: ignore[method-assign]
    result = backend.write("src/a.txt", "should not land")
    assert result.error and "disk full" in result.error
    assert (root / "src" / "a.txt").read_bytes() == original


def test_oversized_file_blocks_the_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    big = root / "big.txt"
    big.write_bytes(b"x" * (20_000_001))
    backend = WorkspaceBackend(root, Redactor(), SnapshotStore(root))
    result = backend.write("big.txt", "small")
    assert result.error and "undo limit" in result.error
    assert big.stat().st_size == 20_000_001


def test_changed_lines_reports_edited_ranges(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, store, backend = setup
    backend.write("src/a.txt", "first\nadded\n")
    assert store.changed_lines("src/a.txt") == [(2, 2)]

    backend.write("src/a.txt", "changed\nadded\n")
    assert store.changed_lines("src/a.txt") == [(1, 1)]

    assert store.changed_lines("src/untouched.txt") == []


def test_changed_lines_for_a_created_file_marks_everything(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    _root, store, backend = setup
    backend.write("src/fresh.txt", "a\nb\nc\n")
    assert store.changed_lines("src/fresh.txt") == [(1, 3)]


def test_revert_route_restores_the_file(
    setup: tuple[Path, SnapshotStore, WorkspaceBackend],
) -> None:
    root, store, backend = setup
    backend.write("src/a.txt", "second\n")
    target = store.newest_for("src/a.txt")
    assert target is not None

    with TestClient(create_app("token")) as client:
        headers = {"Authorization": "Bearer token"}
        response = client.post(
            f"/snapshots/{target.id}/revert",
            json={"workspace": str(root)},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["path"] == "src/a.txt"
        assert (
            client.post(
                "/snapshots/does-not-exist/revert", json={"workspace": str(root)}, headers=headers
            ).status_code
            == 404
        )
    assert (root / "src" / "a.txt").read_bytes() == b"first\n"
