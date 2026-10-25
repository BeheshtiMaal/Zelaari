"""Installation refuses unsafe input before any proposal exists."""

import stat
import zipfile
from pathlib import Path

import pytest

from skills import install

GOOD = "---\nname: {name}\ndescription: A test skill.\n---\nBody\n"


def folder(tmp_path: Path, name: str = "good") -> Path:
    path = tmp_path / name
    path.mkdir()
    (path / "SKILL.md").write_text(GOOD.format(name=name), encoding="utf-8")
    (path / "notes.md").write_text("not part of a skill", encoding="utf-8")
    (path / "scripts").mkdir()
    (path / "scripts" / "run.sh").write_text("echo ok\n", encoding="utf-8")
    return path


def test_a_folder_keeps_only_the_documented_files(tmp_path: Path) -> None:
    files = install.from_folder(folder(tmp_path))
    assert sorted(files) == ["SKILL.md", "scripts/run.sh"]


def test_a_folder_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        install.from_folder(tmp_path / "absent")


def test_non_utf8_is_refused(tmp_path: Path) -> None:
    path = folder(tmp_path)
    (path / "scripts" / "bin.sh").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ValueError, match="text files"):
        install.from_folder(path)


def test_an_oversized_file_is_refused(tmp_path: Path) -> None:
    path = folder(tmp_path)
    (path / "references").mkdir()
    (path / "references" / "huge.md").write_text("x" * 70_000, encoding="utf-8")
    with pytest.raises(ValueError, match="larger than"):
        install.from_folder(path)


@pytest.mark.parametrize("entry", ["../evil.md", "/etc/passwd", "a/../../b.md", "C:/x.md"])
def test_a_zip_cannot_escape(tmp_path: Path, entry: str) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(entry, "x")
    with pytest.raises(ValueError):
        install.from_zip(archive)


def test_a_zip_symlink_is_refused(tmp_path: Path) -> None:
    archive = tmp_path / "link.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        info = zipfile.ZipInfo("skill/link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(info, "/etc/passwd")
        bundle.writestr("skill/SKILL.md", GOOD.format(name="link"))
    with pytest.raises(ValueError, match="symlink"):
        install.from_zip(archive)


def test_a_zip_with_too_many_entries_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(install, "MAX_FILES", 3)
    archive = tmp_path / "many.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for index in range(5):
            bundle.writestr("s/SKILL.md" if index == 0 else f"s/scripts/{index}.sh", "x")
    with pytest.raises(ValueError, match="limited to"):
        install.from_zip(archive)


def test_an_oversized_zip_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install, "MAX_ZIP_BYTES", 10)
    archive = tmp_path / "big.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("SKILL.md", GOOD.format(name="big"))
    with pytest.raises(ValueError, match="larger than 8 MB"):
        install.from_zip(archive)


def test_a_zip_with_one_wrapper_folder_works(tmp_path: Path) -> None:
    archive = tmp_path / "ok.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("wrapped/SKILL.md", GOOD.format(name="wrapped"))
        bundle.writestr("wrapped/scripts/run.sh", "echo ok\n")
        bundle.writestr("wrapped/other.txt", "ignored")
    files = install.from_zip(archive)
    assert sorted(files) == ["SKILL.md", "scripts/run.sh"]


def test_candidate_refuses_a_blocked_skill() -> None:
    files = {"SKILL.md": "---\nname: risky\ndescription: x\n---\nrm -rf /\n"}
    with pytest.raises(ValueError, match="security scan"):
        install.candidate(files)


def test_candidate_needs_a_skill_file() -> None:
    with pytest.raises(ValueError, match="SKILL.md"):
        install.candidate({"scripts/run.sh": "echo ok"})


def test_candidate_rejects_an_unexpected_file() -> None:
    files = {"SKILL.md": GOOD.format(name="x"), "run.exe": "MZ"}
    with pytest.raises(ValueError, match="Unexpected file"):
        install.candidate(files)


def test_candidate_reports_the_scan() -> None:
    found = install.candidate({"SKILL.md": GOOD.format(name="x")})
    assert found.name == "x"
    assert found.scan.status == "clean"


@pytest.mark.parametrize(
    "url",
    ["https://example.test/skill.git", "ssh://git@example.test/skill", "file:///tmp/skill"],
)
def test_git_urls_are_checked(url: str) -> None:
    assert install.validate_git_url(url) == url


@pytest.mark.parametrize("url", ["http://example.test/x", "git@example.test:x", "example.test"])
def test_unsafe_git_urls_are_refused(url: str) -> None:
    with pytest.raises(ValueError):
        install.validate_git_url(url)


def test_from_write_renders_a_valid_skill() -> None:
    files = install.from_write("made", "Made in the hub.", "Body", "/made", "docs", True)
    found = install.candidate(files)
    assert found.name == "made"
    assert "requires_approval: true" in files["SKILL.md"]
    assert "command: /made" in files["SKILL.md"]
