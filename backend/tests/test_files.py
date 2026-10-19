"""`GET /files`: the tree, the system-files toggle, changed lines and the jail."""

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from server.app import create_app
from tools.jail import resolve
from tools.snapshot import SnapshotStore

HEADERS = {"Authorization": "Bearer token"}


def client() -> TestClient:
    return TestClient(create_app("token"))


def listing(root: Path, **params: str | bool) -> Any:
    with client() as app:
        response = app.get(
            "/files",
            headers=HEADERS,
            params={"workspace": str(root), **params},
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_directory_listing_puts_folders_first(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "README.md").write_bytes(b"# hi\n")

    payload = listing(tmp_path)

    assert payload["kind"] == "dir"
    assert payload["path"] == ""
    names = [entry["name"] for entry in payload["entries"]]
    assert names == ["src", "README.md"]
    assert payload["entries"][0]["kind"] == "dir"
    assert payload["entries"][1]["size"] == 5


def test_harness_is_hidden_until_the_toggle_is_on(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "rules.json").write_text("{}", encoding="utf-8")

    hidden = listing(tmp_path)
    assert [entry["name"] for entry in hidden["entries"]] == ["a.txt"]

    shown = listing(tmp_path, system=True)
    assert {entry["name"] for entry in shown["entries"]} == {"a.txt", ".harness"}

    inside = listing(tmp_path, path=".harness", system=True)
    assert [entry["name"] for entry in inside["entries"]] == ["rules.json"]


def test_harness_is_refused_when_the_toggle_is_off(tmp_path: Path) -> None:
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "rules.json").write_text("{}", encoding="utf-8")

    with client() as app:
        response = app.get(
            "/files",
            headers=HEADERS,
            params={"workspace": str(tmp_path), "path": ".harness/rules.json"},
        )

    assert response.status_code == 400


def test_file_returns_text_and_changed_lines(tmp_path: Path) -> None:
    target = tmp_path / "a.txt"
    target.write_text("one\ntwo\n", encoding="utf-8")
    store = SnapshotStore(tmp_path)
    store.capture(resolve(tmp_path, "a.txt"), tool="write_file")
    target.write_text("one\nTWO\nthree\n", encoding="utf-8")

    payload = listing(tmp_path, path="a.txt")

    assert payload["kind"] == "file"
    content = payload["file"]
    assert content["path"] == "a.txt"
    assert content["text"] == "one\nTWO\nthree"
    assert content["binary"] is False
    assert content["pending_approval"] is False
    assert content["changed_lines"] == [[2, 3]]


def test_binary_file_is_flagged_not_mangled(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02binary")

    payload = listing(tmp_path, path="blob.bin")

    content = payload["file"]
    assert content["binary"] is True
    assert content["text"] == ""
    assert content["changed_lines"] == []


def test_entry_is_marked_changed_after_a_snapshot(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("two\n", encoding="utf-8")
    SnapshotStore(tmp_path).capture(resolve(tmp_path, "a.txt"), tool="write_file")

    payload = listing(tmp_path)

    changed = {entry["name"]: entry["changed"] for entry in payload["entries"]}
    assert changed == {"a.txt": True, "b.txt": False}


def test_traversal_and_absolute_paths_are_refused(tmp_path: Path) -> None:
    with client() as app:
        for path in ["../secret.txt", "C:/Windows/win.ini", "\\\\host\\share", "/etc/passwd"]:
            response = app.get(
                "/files",
                headers=HEADERS,
                params={"workspace": str(tmp_path), "path": path},
            )
            assert response.status_code == 400, path


def test_pending_approval_badges_the_path(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")

    class Paused:
        def pending_paths(self) -> set[str]:
            return {"a.txt"}

        async def close(self) -> None:
            return None

    app = create_app("token", cast(Any, Paused()))

    with TestClient(app) as test:
        response = test.get(
            "/files",
            headers=HEADERS,
            params={"workspace": str(tmp_path), "path": "a.txt"},
        )

    assert response.status_code == 200
    assert response.json()["file"]["pending_approval"] is True
