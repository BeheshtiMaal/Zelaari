import subprocess
from pathlib import Path

import pytest

from store.secrets import Redactor
from tools.jail import ReadOnlyBackend, storage_path, workspace_root


def test_read_and_deny_escapes(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.txt").write_text("real content", encoding="utf-8")
    secret = tmp_path / "secret.txt"
    secret.write_text("outside", encoding="utf-8")
    backend = ReadOnlyBackend(root, Redactor())
    result = backend.read("src/a.txt")
    assert result.file_data is not None and result.file_data["content"] == "real content"
    assert backend.read("/src/a.txt").file_data == result.file_data
    for path in [
        "../secret.txt",
        str(secret),
        "C:secret.txt",
        "\\secret.txt",
        "\\\\host\\share\\secret",
        "src/a.txt:secret",
        "NUL",
        ".harness/config.json",
    ]:
        assert backend.read(path).error, path
    assert backend.write("new.txt", "no").error
    assert backend.edit("src/a.txt", "real", "changed").error
    assert not (root / "new.txt").exists()
    assert (root / "src" / "a.txt").read_text() == "real content"


def test_real_symlink_and_junction_escapes(tmp_path: Path) -> None:
    root, outside = tmp_path / "workspace", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    link = root / "symlink"
    link.symlink_to(outside, target_is_directory=True)
    junction = root / "junction"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)], check=True, capture_output=True
    )
    try:
        backend = ReadOnlyBackend(root, Redactor())
        for name in ["symlink", "junction"]:
            assert backend.read(f"{name}/secret.txt").error
            assert backend.read(f"{name}/missing.txt").error
    finally:
        link.unlink()
        junction.rmdir()


def test_storage_junction_escape_and_invalid_roots(tmp_path: Path) -> None:
    root, outside = tmp_path / "workspace", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / ".harness"
    link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError):
            storage_path(root, "runs/a/events.jsonl")
    finally:
        link.unlink()
    for value in [Path.home(), Path(tmp_path.anchor)]:
        with pytest.raises(ValueError):
            workspace_root(str(value))
