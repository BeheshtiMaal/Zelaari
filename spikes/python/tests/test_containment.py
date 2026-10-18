import os
import subprocess
from pathlib import Path

import pytest

from containment import contained


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "internal.txt").write_text("fixture", encoding="utf8")
    return root


def test_internal_case_and_separators(workspace: Path) -> None:
    assert contained(workspace, "internal.txt").read_text() == "fixture"
    assert contained(workspace, str(workspace).upper() + "/INTERNAL.txt").read_text() == "fixture"
    assert contained(workspace, "sub/../internal.txt").read_text() == "fixture"
    assert contained(workspace, "new.txt").parent == workspace.resolve()


@pytest.mark.parametrize(
    "value",
    [
        "../outside.txt",
        "..\\outside.txt",
        "E:relative.txt",
        "\\\\invalid.invalid\\share\\file.txt",
        "\\rooted.txt",
    ],
)
def test_ambiguous_and_escape_paths(workspace: Path, value: str) -> None:
    with pytest.raises(ValueError):
        contained(workspace, value)


def test_absolute_and_sibling_prefix(workspace: Path) -> None:
    for target in [workspace.parent / "outside.txt", workspace.parent / "workspace-other/file.txt"]:
        with pytest.raises(ValueError):
            contained(workspace, str(target))


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_link_escape(workspace: Path, kind: str) -> None:
    outside = workspace.parent / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("fixture", encoding="utf8")
    link = workspace / "linked"
    if kind == "symlink":
        # Permission errors intentionally fail this validation, never skip it.
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if error.winerror != 1314:
                raise
            pytest.fail(
                "Windows refused the real symlink fixture (WinError 1314). "
                "Enable Developer Mode in Windows Settings > Update & Security > "
                "For developers, or run this test from a session with "
                "SeCreateSymbolicLinkPrivilege. Containment has not been tested "
                "for symlinks; this check remains failed until creation succeeds.",
                pytrace=False,
            )
    else:
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    try:
        for suffix in ["secret.txt", "not-yet-created.txt"]:
            with pytest.raises(ValueError):
                contained(workspace, str(link / suffix))
    finally:
        os.rmdir(link)  # Remove link only, never traverse its target.
