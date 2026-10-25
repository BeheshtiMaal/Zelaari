"""Discovery: three roots, nearest wins, bounded, and blind to links."""

import os
from pathlib import Path

import pytest

from skills import loader
from skills.types import SkillsState


def write(root: Path, name: str, description: str = "Does a thing.", extra: str = "") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n{extra}---\nBody of {name}\n",
        encoding="utf-8",
    )
    return folder


@pytest.fixture
def roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """(bundled root, app-data root, workspace root)."""
    bundled, app, workspace = tmp_path / "bundled", tmp_path / "appdata", tmp_path / "workspace"
    for root in (bundled, app / "skills", workspace / ".harness" / "skills"):
        root.mkdir(parents=True)
    monkeypatch.setenv(loader.BUNDLED_ENV, str(bundled))
    return bundled, app, workspace


def test_workspace_beats_user_beats_bundled(roots: tuple[Path, Path, Path]) -> None:
    bundled, app, workspace = roots
    write(bundled, "shared", "bundled copy")
    write(bundled, "only-bundled")
    write(app / "skills", "shared", "user copy")
    write(workspace / ".harness" / "skills", "shared", "workspace copy")

    found = {record.name: record for record in loader.discover(workspace, app)}
    assert found["shared"].description == "workspace copy"
    assert found["shared"].source == "workspace"
    assert found["only-bundled"].source == "bundled"
    assert [record.name for record in loader.discover(workspace, app)] == [
        "only-bundled",
        "shared",
    ]


def test_user_root_wins_over_bundled(roots: tuple[Path, Path, Path]) -> None:
    bundled, app, workspace = roots
    write(bundled, "shared", "bundled copy")
    write(app / "skills", "shared", "user copy")
    found = loader.discover(workspace, app)
    assert (found[0].source, found[0].description) == ("user", "user copy")
    assert found[0].path == "user/skills/shared"


def test_missing_roots_are_empty(roots: tuple[Path, Path, Path], tmp_path: Path) -> None:
    _, _, workspace = roots
    assert loader.discover(workspace, tmp_path / "absent") == []
    assert loader.discover(None, None) == []


def test_broken_folder_is_listed_with_a_problem(roots: tuple[Path, Path, Path]) -> None:
    _, _, workspace = roots
    folder = workspace / ".harness" / "skills" / "broken"
    folder.mkdir()
    (folder / "SKILL.md").write_text("---\nname: broken\n---\n", encoding="utf-8")
    found = loader.discover(workspace, None)
    assert found[0].problem is not None
    assert found[0].enabled is False
    assert "description is required" in (found[0].problem or "")


def test_a_symlinked_folder_is_ignored(roots: tuple[Path, Path, Path], tmp_path: Path) -> None:
    _, _, workspace = roots
    real = write(tmp_path / "outside", "linked")
    link = workspace / ".harness" / "skills" / "linked"
    try:
        os.symlink(real, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this host cannot create directory symlinks")
    assert loader.discover(workspace, None) == []


def test_the_folder_bound_stops_discovery(
    roots: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, workspace = roots
    monkeypatch.setattr(loader, "MAX_SKILLS_PER_ROOT", 3)
    for index in range(5):
        write(workspace / ".harness" / "skills", f"skill-{index}")
    assert len(loader.discover(workspace, None)) == 3


def test_overrides_win_over_the_file(roots: tuple[Path, Path, Path]) -> None:
    _, _, workspace = roots
    write(workspace / ".harness" / "skills", "off-by-default", extra="enabled: false\n")
    write(workspace / ".harness" / "skills", "on-by-default")
    found = {record.name: record for record in loader.discover(workspace, None)}
    assert found["off-by-default"].enabled is False
    assert found["on-by-default"].enabled is True

    state = SkillsState(overrides={"off-by-default": True, "on-by-default": False})
    found = {record.name: record for record in loader.discover(workspace, None, state)}
    assert found["off-by-default"].enabled is True
    assert found["on-by-default"].enabled is False


def test_detail_reads_the_body_and_rescans(roots: tuple[Path, Path, Path]) -> None:
    _, _, workspace = roots
    folder = write(workspace / ".harness" / "skills", "mine")
    (folder / "scripts").mkdir()
    (folder / "scripts" / "run.sh").write_text("echo ok\n", encoding="utf-8")
    record = loader.discover(workspace, None)[0]
    assert record.scan.status == "clean"
    assert record.scan.scripts == ["scripts/run.sh"]

    (folder / "scripts" / "run.sh").write_text("rm -rf /\n", encoding="utf-8")
    detail = loader.detail(record, workspace, None)
    assert detail.scan.status == "blocked"
    assert detail.body == "Body of mine"
    assert detail.scan.scripts == ["scripts/run.sh"]


def test_token_cost_is_the_summary_line(roots: tuple[Path, Path, Path]) -> None:
    _, _, workspace = roots
    write(workspace / ".harness" / "skills", "short", "Tiny.")
    record = loader.discover(workspace, None)[0]
    assert 1 <= record.tokens <= 20
