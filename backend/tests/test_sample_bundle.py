"""Which of the two real layouts the sample is found in, and what happens when neither is.

The copy semantics — once, and never over an edited copy — are proven in
`test_sample_workspace.py`. This file is only about resolution, because a packaged app
and a source checkout look for the sample in different places and only the checkout
layout was ever exercised by a test.
"""

import sys
from pathlib import Path

import pytest

from appdata import sample


def project(root: Path, readme: str = "# Sample project\n") -> Path:
    """A sample project at `root`, laid out the way the bundle ships it."""
    bundle = root / "examples" / sample.NAME
    skill = bundle / ".harness" / "skills" / "read-framework-docs"
    skill.mkdir(parents=True)
    (bundle / "README.md").write_text(readme, encoding="utf-8")
    (skill / "SKILL.md").write_text(
        "---\nname: read-framework-docs\ndescription: Read docs.\nenabled: false\n---\n",
        encoding="utf-8",
    )
    return bundle


def in_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "checkout") -> Path:
    """Point the module at `name` as if it were `<repo>/backend/appdata/sample.py`."""
    module = tmp_path / name / "backend" / "appdata" / "sample.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(sample, "__file__", str(module))
    return tmp_path / name


def test_a_packaged_engine_finds_the_sample_beside_its_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_checkout(tmp_path, monkeypatch)
    bundle = project(tmp_path / "build" / "engine" / "engine")
    monkeypatch.setattr(
        sys, "executable", str(tmp_path / "build" / "engine" / "engine" / "engine.exe")
    )

    assert sample.source() == bundle
    assert (bundle / "README.md").is_file()


def test_the_checkout_wins_when_both_layouts_are_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = in_checkout(tmp_path, monkeypatch)
    mine = project(checkout)
    project(tmp_path / "build", readme="# Stale copy from an older build\n")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "build" / "engine.exe"))

    assert sample.source() == mine


def test_a_tree_with_neither_layout_reports_no_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_checkout(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bundle" / "engine.exe"))

    assert sample.source() is None


def test_an_examples_folder_without_the_readme_is_not_a_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The failure the build script now refuses: a copied folder that arrived empty."""
    in_checkout(tmp_path, monkeypatch)
    (tmp_path / "bundle" / "examples" / sample.NAME).mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "bundle" / "engine.exe"))

    assert sample.source() is None
