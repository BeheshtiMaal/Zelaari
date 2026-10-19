"""`run_command` behaviour: shells, timeout kill, paging and environment scrubbing."""

import json
import time
from pathlib import Path

import psutil
import pytest

from store.secrets import Redactor
from tools.command import DEFAULT_TIMEOUT, MAX_LINES, CommandRunner, build_run_command, pick_shell
from tools.jail import JailError

pytestmark = pytest.mark.skipif(
    __import__("sys").platform != "win32", reason="Windows process-tree semantics"
)


@pytest.fixture()
def runner(tmp_path: Path) -> CommandRunner:
    return CommandRunner(tmp_path, Redactor(), secrets=["canary-secret-value"])


def test_powershell_is_the_default_shell() -> None:
    assert pick_shell().name == "powershell"


def test_runs_a_real_command(runner: CommandRunner) -> None:
    result = runner.run("Write-Output 'hello from the harness'")
    assert result.exit_code == 0
    assert "hello from the harness" in result.output
    assert result.shell == "powershell"
    assert result.duration_ms >= 0
    assert result.timed_out is False


def test_cmd_fallback_runs_when_powershell_is_absent(
    runner: CommandRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def only_cmd(name: str) -> str | None:
        return "C:\\Windows\\System32\\cmd.exe" if name == "cmd.exe" else None

    monkeypatch.setattr("tools.command.shutil.which", only_cmd)
    result = runner.run("echo hello-from-cmd")
    assert result.shell == "cmd"
    assert result.exit_code == 0
    assert "hello-from-cmd" in result.output


def test_non_zero_exit_is_a_normal_result(runner: CommandRunner) -> None:
    result = runner.run("exit 3")
    assert result.exit_code == 3
    assert result.timed_out is False


def test_timeout_kills_the_whole_process_tree(runner: CommandRunner, tmp_path: Path) -> None:
    started = time.monotonic()
    result = runner.run(
        "$p = Start-Process powershell -ArgumentList '-NoProfile','-Command','Start-Sleep 60' "
        "-PassThru; Set-Content -Path child.pid -Value $p.Id; Start-Sleep 60",
        timeout=3,
    )
    elapsed = time.monotonic() - started

    assert result.timed_out is True
    assert result.killed_tree is True
    assert result.exit_code is None
    assert elapsed < 30

    pid_file = tmp_path / "child.pid"
    assert pid_file.is_file(), "the command never recorded its child"
    child = int(pid_file.read_text(encoding="utf-8").strip())

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not psutil.pid_exists(child):
            break
        time.sleep(0.2)
    assert not psutil.pid_exists(child), "a descendant survived the timeout"


def test_default_timeout_is_reported(runner: CommandRunner) -> None:
    result = runner.run("Write-Output 'ok'")
    assert result.timeout_seconds == DEFAULT_TIMEOUT


def test_output_is_capped_and_pageable(runner: CommandRunner) -> None:
    result = runner.run("1..500 | ForEach-Object { $_ }")
    lines = result.output.splitlines()
    assert result.total_lines == 500
    assert len([line for line in lines if line.strip().isdigit()]) == MAX_LINES
    assert "more lines" in result.output
    assert result.truncated is True

    second = runner.run("1..500 | ForEach-Object { $_ }", offset=200)
    assert second.output.splitlines()[0].strip() == "201"


def test_giant_single_line_is_cut_off(runner: CommandRunner) -> None:
    result = runner.run("Write-Output ('x' * 1200000)")
    assert result.truncated is True
    assert "capture limit" in result.output
    assert len(result.output) < 1_200_000


def test_cwd_outside_the_workspace_is_rejected(runner: CommandRunner, tmp_path: Path) -> None:
    outside = tmp_path.parent
    with pytest.raises(JailError):
        runner.run("Write-Output 'nope'", cwd=str(outside))


def test_child_environment_is_scrubbed(
    runner: CommandRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-canary-openai")
    monkeypatch.setenv("MY_SERVICE_TOKEN", "canary-token-value")
    monkeypatch.setenv("LANGSMITH_API_KEY", "canary-langsmith")
    monkeypatch.setenv("CODEHARNESS_LAUNCH_TOKEN", "canary-secret-value")

    result = runner.run('Get-ChildItem Env: | ForEach-Object { "$($_.Name)=$($_.Value)" }')
    assert result.exit_code == 0
    assert "canary-openai" not in result.output
    assert "canary-token-value" not in result.output
    assert "canary-langsmith" not in result.output
    assert "canary-secret-value" not in result.output
    assert "OPENAI_API_KEY" not in result.output


def test_tool_wrapper_returns_json(runner: CommandRunner) -> None:
    tool = build_run_command(runner)
    payload = json.loads(tool.invoke({"command": "Write-Output 'tool-path'"}))
    assert payload["exit_code"] == 0
    assert "tool-path" in payload["output"]
    assert payload["shell"] == "powershell"
