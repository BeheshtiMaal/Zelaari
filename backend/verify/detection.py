"""Read-only test command detection: pytest and `npm test` only, inside the workspace.

Nothing here runs a command or leaves the workspace. Every file read is bounded and no
symlink or junction is followed, so a link inside `tests/` cannot leak host paths.
"""

import json
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

MAX_ENTRIES = 5000
MAX_FILE_BYTES = 1_000_000
SKIP = {".harness", ".git", "node_modules"}
PYTEST_COMMAND = "pytest -q"
NPM_COMMAND = "npm test"
NPM_PLACEHOLDER = "no test specified"

Source = Literal["custom", "pytest.ini", "pyproject.toml", "tests", "package.json", "none"]

PYTEST_DEPENDENCY = re.compile(
    r"""(?m)(?:^|[\s\[,"'])pytest(\[[^\]\n]*\])?\s*(?:[<>=!~,"'\]]|$)"""
)


class Detection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str | None = None
    source: Source = "none"


def link(path: Path) -> bool:
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return True


def regular_file(path: Path) -> bool:
    return not link(path) and path.is_file()


def read_text(path: Path) -> str:
    with path.open("rb") as handle:
        raw = handle.read(MAX_FILE_BYTES)
    try:
        return raw.decode("utf-8", errors="replace")
    except UnicodeError:  # pragma: no cover - errors="replace" already prevents this
        return ""


def mentions_pytest(path: Path) -> bool:
    text = read_text(path)
    return "[tool.pytest" in text or PYTEST_DEPENDENCY.search(text) is not None


def python_tests(root: Path) -> bool:
    """A `tests/` folder with at least one pytest-style module, walked without links."""
    directory = root / "tests"
    if link(directory) or not directory.is_dir():
        return False
    seen = 0
    for current, directories, files in os.walk(directory, followlinks=False):
        directories[:] = [
            name
            for name in directories
            if name.casefold() not in SKIP and not link(Path(current) / name)
        ]
        for name in files:
            seen += 1
            if seen > MAX_ENTRIES:
                return False
            lowered = name.casefold()
            if lowered.endswith(".py") and (
                lowered.startswith("test_") or lowered.endswith("_test.py")
            ):
                return True
    return False


def npm_test(root: Path) -> bool:
    path = root / "package.json"
    if not regular_file(path):
        return False
    try:
        document = json.loads(read_text(path))
    except ValueError:
        return False
    if not isinstance(document, dict):
        return False
    scripts = document.get("scripts")
    if not isinstance(scripts, dict):
        return False
    command = scripts.get("test")
    if not isinstance(command, str) or not command.strip():
        return False
    return NPM_PLACEHOLDER not in command.casefold()


def detect(root: Path, command: str | None = None) -> Detection:
    """Custom setting wins, then pytest, then `npm test`; the source names the evidence."""
    if command is not None and command.strip():
        return Detection(command=command.strip(), source="custom")
    if regular_file(root / "pytest.ini"):
        return Detection(command=PYTEST_COMMAND, source="pytest.ini")
    pyproject = root / "pyproject.toml"
    if regular_file(pyproject) and mentions_pytest(pyproject):
        return Detection(command=PYTEST_COMMAND, source="pyproject.toml")
    if python_tests(root):
        return Detection(command=PYTEST_COMMAND, source="tests")
    if npm_test(root):
        return Detection(command=NPM_COMMAND, source="package.json")
    return Detection()
