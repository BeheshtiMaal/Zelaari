"""Phase 3 jail and filesystem tool behaviour. Every link is real, never mocked."""

import subprocess
from pathlib import Path

import pytest

from store.secrets import Redactor
from tools.fs import WorkspaceBackend
from tools.jail import JailError, storage_path, workspace_root

ESCAPES = [
    "../secret.txt",
    "..",
    "src/../../secret.txt",
    "C:secret.txt",
    "\\secret.txt",
    "\\\\host\\share\\secret",
    "src/a.txt:secret",
    "NUL",
    "CON",
    ".harness/config.json",
    ".harness/runs/x/events.jsonl",
]


@pytest.fixture()
def workspace(tmp_path: Path) -> tuple[Path, Path, WorkspaceBackend]:
    root, outside = tmp_path / "workspace", tmp_path / "outside"
    (root / "src").mkdir(parents=True)
    outside.mkdir()
    (root / "src" / "a.txt").write_bytes(b"real content\n")
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    return root, outside, WorkspaceBackend(root, Redactor())


def test_read_and_deny_escapes(workspace: tuple[Path, Path, WorkspaceBackend]) -> None:
    root, outside, backend = workspace
    result = backend.read("src/a.txt")
    assert result.file_data is not None and result.file_data["content"] == "real content\n"
    assert backend.read("/src/a.txt").file_data == result.file_data

    for path in ESCAPES:
        assert backend.read(path).error, path
    assert backend.read(str(outside / "secret.txt")).error


@pytest.mark.parametrize("form", ["../secret.txt", "\\\\host\\share\\secret", "NUL", ".harness/x"])
def test_every_tool_rejects_escape_forms(
    workspace: tuple[Path, Path, WorkspaceBackend], form: str
) -> None:
    _root, _outside, backend = workspace
    assert backend.read(form).error
    assert backend.write(form, "x").error
    assert backend.edit(form, "a", "b").error
    assert backend.delete(form).error
    assert backend.ls(form).error
    assert backend.grep("x", form).error


def test_real_symlink_and_junction_escape_all_tools(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, outside, backend = workspace
    link = root / "symlink"
    link.symlink_to(outside, target_is_directory=True)
    junction = root / "junction"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)], check=True, capture_output=True
    )
    try:
        for name in ("symlink", "junction"):
            assert backend.read(f"{name}/secret.txt").error
            assert backend.write(f"{name}/new.txt", "x").error
            assert backend.edit(f"{name}/secret.txt", "outside", "changed").error
            assert backend.delete(f"{name}/secret.txt").error
            assert not (outside / "new.txt").exists()
            assert (outside / "secret.txt").read_text() == "outside"
    finally:
        link.unlink()
        junction.rmdir()


def test_harness_storage_is_unreachable_through_every_tool(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    harness = root / ".harness"
    harness.mkdir()
    (harness / "rules.json").write_text("{}", encoding="utf-8")
    (root / "src" / "b.txt").write_text("visible", encoding="utf-8")

    assert backend.read(".harness/rules.json").error
    assert backend.write(".harness/rules.json", "{}").error
    assert backend.delete(".harness/rules.json").error
    assert all("harness" not in str(entry["path"]) for entry in backend.ls("/").entries or [])
    assert all(
        ".harness" not in str(entry["path"]) for entry in backend.glob("**/*.json").matches or []
    )
    assert backend.grep("visible", "/").matches is not None
    assert all(
        ".harness" not in str(match["path"]) for match in backend.grep("{}", "/").matches or []
    )


def test_write_creates_and_overwrites_atomically(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    created = backend.write("src/new/nested.txt", "first")
    assert created.error is None and created.path == "/src/new/nested.txt"
    assert (root / "src" / "new" / "nested.txt").read_text(encoding="utf-8") == "first"

    assert backend.write("src/new/nested.txt", "second").error is None
    assert (root / "src" / "new" / "nested.txt").read_text(encoding="utf-8") == "second"
    assert not list((root / "src" / "new").glob(".harness-tmp-*"))


def test_atomic_write_rollback_leaves_original_intact(
    workspace: tuple[Path, Path, WorkspaceBackend], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _outside, backend = workspace
    original = (root / "src" / "a.txt").read_bytes()

    def explode(_src: object, _dst: object) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr("tools.atomic.os.replace", explode)
    assert backend.write("src/a.txt", "half-written").error
    assert (root / "src" / "a.txt").read_bytes() == original
    assert not list((root / "src").glob(".harness-tmp-*"))


def test_edit_requires_uniqueness_and_reports_occurrences(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    target = root / "src" / "dup.txt"
    target.write_text("a\na\nb\n", encoding="utf-8")

    ambiguous = backend.edit("src/dup.txt", "a", "z")
    assert ambiguous.error and "2 times" in ambiguous.error
    assert target.read_text(encoding="utf-8") == "a\na\nb\n"

    replaced = backend.edit("src/dup.txt", "a", "z", replace_all=True)
    assert replaced.occurrences == 2
    assert target.read_text(encoding="utf-8") == "z\nz\nb\n"

    assert backend.edit("src/dup.txt", "missing", "z").error
    assert backend.edit("src/dup.txt", "z", "z").error


def test_delete_refuses_directories_and_missing_paths(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    assert backend.delete("src").error
    assert (root / "src").is_dir()
    assert backend.delete("src/missing.txt").error
    assert backend.delete("src/a.txt").error is None
    assert not (root / "src" / "a.txt").exists()


def test_binary_and_oversized_reads_are_rejected(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    (root / "blob.bin").write_bytes(b"\x00\x01\x02binary")
    assert backend.read("blob.bin").error

    big = root / "big.txt"
    big.write_text("x" * 2_000_001, encoding="utf-8")
    assert backend.read("big.txt").error


def test_storage_junction_escape_and_invalid_roots(tmp_path: Path) -> None:
    root, outside = tmp_path / "workspace", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / ".harness"
    link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(JailError):
            storage_path(root, "runs/a/events.jsonl")
    finally:
        link.unlink()
    for value in [Path.home(), Path(tmp_path.anchor)]:
        with pytest.raises(JailError):
            workspace_root(str(value))
