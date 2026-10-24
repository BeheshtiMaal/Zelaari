"""Detection matrix: pytest and `npm test` only, read-only, inside the workspace."""

import json
import os
from pathlib import Path

import pytest

from verify.detection import NPM_COMMAND, PYTEST_COMMAND, detect


def test_custom_command_wins(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    assert detect(tmp_path, "uv run pytest -x").model_dump() == {
        "command": "uv run pytest -x",
        "source": "custom",
    }
    assert detect(tmp_path, "   ").command == PYTEST_COMMAND
    assert detect(tmp_path, None).source == "pytest.ini"


def test_pytest_ini(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    assert detect(tmp_path) == detect(tmp_path, None)
    assert (detect(tmp_path).command, detect(tmp_path).source) == (PYTEST_COMMAND, "pytest.ini")


@pytest.mark.parametrize(
    "body",
    [
        "[project]\nname = 'x'\ndependencies = ['pytest>=8']\n",
        "[tool.pytest.ini_options]\naddopts = '-q'\n",
        "[dependency-groups]\ndev = [\n  \"pytest\",\n]\n",
        "[project.optional-dependencies]\ntest = [\"pytest[django]<9\"]\n",
    ],
)
def test_pyproject_mentions_pytest(tmp_path: Path, body: str) -> None:
    (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")
    found = detect(tmp_path)
    assert (found.command, found.source) == (PYTEST_COMMAND, "pyproject.toml")


def test_pyproject_without_pytest_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert detect(tmp_path).model_dump() == {"command": None, "source": "none"}


def test_tests_directory(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    module = tmp_path / "tests" / "test_parser.py"
    module.write_text("def test_ok():\n    pass\n", encoding="utf-8")
    assert (detect(tmp_path).command, detect(tmp_path).source) == (PYTEST_COMMAND, "tests")


def test_tests_directory_needs_a_pytest_style_module(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "helpers.py").write_text("x = 1\n", encoding="utf-8")
    assert detect(tmp_path).source == "none"


def test_nested_tests_directory_is_found(tmp_path: Path) -> None:
    nested = tmp_path / "tests" / "unit"
    nested.mkdir(parents=True)
    (nested / "parser_test.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    assert detect(tmp_path).source == "tests"


def test_npm_test_script(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "vitest run"}}), encoding="utf-8"
    )
    found = detect(tmp_path)
    assert (found.command, found.source) == (NPM_COMMAND, "package.json")


@pytest.mark.parametrize(
    "scripts",
    [
        {},
        {"test": ""},
        {"test": "   "},
        {"test": 'echo "Error: no test specified" && exit 1'},
        {"build": "tsc"},
    ],
)
def test_npm_placeholder_and_empty_scripts_are_ignored(
    tmp_path: Path, scripts: dict[str, str]
) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"scripts": scripts}), encoding="utf-8")
    assert detect(tmp_path).source == "none"


def test_broken_package_json_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not json", encoding="utf-8")
    assert detect(tmp_path).source == "none"


def test_pytest_wins_when_both_runners_exist(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\ndependencies = ['pytest']\n", encoding="utf-8"
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"test": "jest"}}), encoding="utf-8"
    )
    assert (detect(tmp_path).command, detect(tmp_path).source) == (PYTEST_COMMAND, "pyproject.toml")


def test_system_folders_are_skipped(tmp_path: Path) -> None:
    for name in (".harness", ".git", "node_modules"):
        folder = tmp_path / "tests" / name
        folder.mkdir(parents=True)
        (folder / "test_hidden.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    assert detect(tmp_path).source == "none"


def test_links_inside_tests_are_not_followed(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "test_secret.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    try:
        os.symlink(outside, tests / "linked", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted on this host")
    assert detect(tmp_path).source == "none"
    assert not any("outside" in str(path) for path in [tmp_path / "tests" / "linked"])


def test_linked_pytest_ini_is_ignored(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-ini"
    outside.write_text("[pytest]\n", encoding="utf-8")
    try:
        os.symlink(outside, tmp_path / "pytest.ini")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted on this host")
    assert detect(tmp_path).source == "none"
