"""R30/R31: a jail block and a command timeout are recognisable, not generic failures.

The renderer decides which card to show from the text it receives, so the two shapes
asserted here are a contract between `tools/` and `src/lib/errors.ts`. The companion
test is `tests/unit/errors.test.ts`.
"""

import json
from pathlib import Path
from typing import Protocol

import pytest

from permissions.rules import RulesEngine
from store.secrets import Redactor
from tools.command import DEFAULT_TIMEOUT, CommandRunner
from tools.fs import WorkspaceBackend
from tools.jail import BLOCK_NOTE, jail_message, workspace_root


class Denial(Protocol):
    """Every tool result exposes the same failure field, whatever else it carries."""

    @property
    def error(self) -> str | None: ...


@pytest.fixture()
def workspace(tmp_path: Path) -> tuple[Path, Path, WorkspaceBackend]:
    root, outside = tmp_path / "workspace", tmp_path / "outside"
    (root / "src").mkdir(parents=True)
    outside.mkdir()
    (root / "src" / "a.txt").write_text("real content\n", encoding="utf-8")
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    return root, outside, WorkspaceBackend(root, Redactor())


# -- the jail card ---------------------------------------------------------


def test_escape_produces_the_shared_sentence(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    result = backend.read("../outside/secret.txt")
    assert result.error == jail_message(root, "../outside/secret.txt")


def test_the_sentence_names_the_resolved_target(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    _root, outside, backend = workspace
    result = backend.read("../outside/secret.txt")
    assert result.error is not None
    assert str(outside / "secret.txt") in result.error
    assert result.error.startswith("Access blocked: ")
    assert result.error.endswith(BLOCK_NOTE)


def test_engine_storage_is_a_block_not_an_ordinary_failure(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, backend = workspace
    result = backend.read(".harness/rules.json")
    assert result.error == jail_message(root, ".harness/rules.json")


def test_every_tool_speaks_the_same_sentence(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    """Each tool names its own target, but all of them use the one sentence."""
    root, _outside, backend = workspace
    attempts: dict[str, Denial] = {
        "read": backend.read("../outside/secret.txt"),
        "ls": backend.ls("../outside"),
        "write": backend.write("../outside/x.txt", "x"),
        "edit": backend.edit("../outside/secret.txt", "a", "b"),
        "delete": backend.delete("../outside/secret.txt"),
    }
    for name, result in attempts.items():
        assert result.error is not None, name
        assert result.error.startswith("Access blocked: "), name
        assert result.error.endswith(BLOCK_NOTE), name
    assert attempts["read"].error == jail_message(root, "../outside/secret.txt")
    assert attempts["ls"].error == jail_message(root, "../outside")


def test_a_missing_file_keeps_the_generic_wording(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    _root, _outside, backend = workspace
    result = backend.read("src/absent.txt")
    assert result.error is not None
    assert "Access blocked" not in result.error
    assert BLOCK_NOTE not in result.error


def test_the_block_sentence_survives_a_resolved_root(tmp_path: Path) -> None:
    root = workspace_root(str(tmp_path))
    message = jail_message(root, "..")
    assert message == f"Access blocked: {tmp_path.parent} is outside the workspace. {BLOCK_NOTE}"


# -- the timeout card ------------------------------------------------------


def test_timeout_result_carries_the_fields_the_card_reads(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, _backend = workspace
    result = CommandRunner(root, Redactor()).run("Start-Sleep -Seconds 5", timeout=1)
    payload = json.loads(json.dumps(result.model_dump(), ensure_ascii=False))
    assert payload["timed_out"] is True
    assert payload["timeout_seconds"] == 1
    assert payload["command"] == "Start-Sleep -Seconds 5"
    assert payload["exit_code"] is None


def test_a_normal_result_is_not_a_timeout(
    workspace: tuple[Path, Path, WorkspaceBackend],
) -> None:
    root, _outside, _backend = workspace
    payload = CommandRunner(root, Redactor()).run("Write-Output hi").model_dump()
    assert payload["timed_out"] is False
    assert payload["exit_code"] == 0


# -- the retry action ------------------------------------------------------


def test_the_300_second_retry_needs_a_fresh_approval(tmp_path: Path) -> None:
    """The card's action cannot reuse the old consent: R10 escalates a longer timeout."""
    engine = RulesEngine(tmp_path, mode="auto")
    allowed = engine.decide("run_command", command="Write-Output hi", timeout=DEFAULT_TIMEOUT)
    escalated = engine.decide("run_command", command="Write-Output hi", timeout=300)
    assert allowed.action == "allow"
    assert escalated.action == "ask"
    assert escalated.reason == f"a timeout above {DEFAULT_TIMEOUT:g}s needs approval"
