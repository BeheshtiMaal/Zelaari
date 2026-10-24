"""`test.result` parsing and emission from the real verification command."""

import asyncio
import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from agent.events import TestResult as ResultEvent
from agent.meter import TokenMeter
from agent.projection import ActivityProjection
from planning.types import ActivityScope
from store.eventlog import EventBus
from store.secrets import Redactor
from verify.results import (
    TestOutcome as Outcome,
)
from verify.results import (
    counts,
    failure_ids,
    matches_verification,
    parse_test_output,
)

PYTEST_FAILING = """\
============================= test session starts =============================
collected 12 items

tests/test_parser.py F...........                                        [100%]

=================================== FAILURES ===================================
___________________________ test_jalali_date ___________________________________

    def test_jalali_date():
>       parse_date("2026/01/05")
E       ValueError: time data '2026/01/05' does not match format '%Y-%m-%d'

tests/test_parser.py:14: ValueError
=========================== short test summary info ============================
FAILED tests/test_parser.py::test_jalali_date - ValueError: time data '2026/01/0...
========================= 1 failed, 11 passed in 0.42s =========================
"""

PYTEST_CLEAN = """\
12 passed, 2 warnings in 0.31s
"""

MOCHA = """\
  invoice parser
    ✓ parses ISO dates
    1 passing (18ms)
    1 failing

  1) invoice parser
       parses slash dates:
     AssertionError: expected 2026-01-05
"""

JEST = """\
Tests:       1 failed, 11 passed, 12 total
Snapshots:   0 total
Time:        1.204 s
"""

VITEST = """\
 Test Files  1 failed | 1 passed (2)
      Tests  1 failed | 11 passed (12)
"""


def outcome(
    text: str, exit_code: int | None = 1, timed_out: bool = False, duration: int = 420
) -> Outcome:
    return parse_test_output(
        command="pytest -q",
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration,
        output=text,
    )


def test_pytest_failure_counts_and_ids() -> None:
    result = outcome(PYTEST_FAILING)
    assert result.status == "failed"
    assert (result.passed, result.failed) == (11, 1)
    assert result.failures == ["tests/test_parser.py::test_jalali_date"]
    assert result.duration_ms == 420
    assert "does not match format" in result.summary


def test_pytest_clean_run() -> None:
    result = outcome(PYTEST_CLEAN, exit_code=0)
    assert (result.status, result.passed, result.failed) == ("passed", 12, None)


def test_pytest_collection_errors_count_as_failed() -> None:
    result = outcome("2 errors in 0.10s\nERROR tests/test_b.py", exit_code=4)
    assert result.status == "failed"
    assert result.failed == 2
    assert result.failures == ["tests/test_b.py"]


def test_mocha_counts() -> None:
    passed, failed = counts(MOCHA)
    assert (passed, failed) == (1, 1)
    assert outcome(MOCHA).failures[0] == "invoice parser"


def test_jest_and_vitest_counts() -> None:
    assert counts(JEST) == (11, 1)
    assert counts(VITEST) == (11, 1)


def test_unknown_counts_stay_none() -> None:
    result = outcome("command not recognized\n", exit_code=1)
    assert (result.status, result.passed, result.failed) == ("failed", None, None)


def test_timeout_status_wins() -> None:
    result = outcome("(no output)\n", exit_code=None, timed_out=True)
    assert result.status == "timeout"
    assert result.exit_code is None


def test_killed_without_exit_code_is_error() -> None:
    assert outcome("", exit_code=None).status == "error"


def test_summary_is_bounded_and_redacted() -> None:
    text = "\n".join(f"line {index} sk-secret" for index in range(200))
    result = parse_test_output(
        command="pytest -q",
        exit_code=1,
        timed_out=False,
        duration_ms=1,
        output=text,
        redact=lambda value: value.replace("sk-secret", "[redacted]"),
    )
    assert len(result.summary) <= 2000
    assert "sk-secret" not in result.summary
    assert "[redacted]" in result.summary


def test_failure_list_is_capped() -> None:
    text = "\n".join(f"FAILED tests/test_{index}.py::test_case" for index in range(30))
    assert len(failure_ids(text)) == 10


@pytest.mark.parametrize(
    "command,verification,expected",
    [
        ("pytest -q", "pytest -q", True),
        ("  pytest   -q  ", "pytest -q", True),
        ("pytest -q tests/test_parser.py", "pytest -q", False),
        ("npm test -- --watchAll=false", "npm test", False),
        ("pytest -x", "pytest -q", False),
        ("pytest -q --co", "pytest -q", False),
        ("python -m pytest -q", "pytest -q", False),
        ("anything", "", False),
    ],
)
def test_command_matching(command: str, verification: str, expected: bool) -> None:
    assert matches_verification(command, verification) is expected


def test_event_round_trips_through_the_wire_model() -> None:
    event = ResultEvent(
        run_id="run",
        seq=3,
        scope=ActivityScope(scope_id="scope"),
        call_id="call",
        command="pytest -q",
        status="failed",
        exit_code=1,
        passed=11,
        failed=1,
        duration_ms=420,
        failures=["tests/test_parser.py::test_jalali_date"],
        summary="1 failed, 11 passed",
    )
    assert json.loads(event.model_dump_json())["type"] == "test.result"


def test_projection_emits_only_for_the_verification_command(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    run_directory = tmp_path / "run"
    run_directory.mkdir()
    bus = EventBus(run_directory / "events.jsonl", "run", Redactor())
    projection = ActivityProjection(bus, TokenMeter(0), 128000, False, "pytest -q")
    scope = ActivityScope(scope_id="scope")
    projection.scopes[()] = scope
    payload = {
        "command": "pytest -q",
        "shell": "powershell",
        "exit_code": 1,
        "duration_ms": 420,
        "output": PYTEST_FAILING,
        "truncated": False,
        "total_lines": 3,
        "offset": 0,
        "timed_out": False,
        "timeout_seconds": 120,
        "killed_tree": False,
    }

    async def scenario() -> None:
        await projection.update(
            (),
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            id="ai-1",
                            tool_calls=[
                                {
                                    "name": "run_command",
                                    "id": "call-1",
                                    "args": {"command": "pytest -q"},
                                }
                            ],
                        )
                    ]
                }
            },
        )
        await projection.update(
            (),
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps(payload), tool_call_id="call-1", name="run_command"
                        )
                    ]
                }
            },
        )
        # A second, non-verification command never produces a test result.
        await projection.update(
            (),
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            id="ai-2",
                            tool_calls=[
                                {
                                    "name": "run_command",
                                    "id": "call-2",
                                    "args": {"command": "git status"},
                                }
                            ],
                        )
                    ]
                }
            },
        )
        await projection.update(
            (),
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps(
                                {**payload, "command": "git status", "exit_code": 0}
                            ),
                            tool_call_id="call-2",
                            name="run_command",
                        )
                    ]
                }
            },
        )

    asyncio.run(scenario())
    results = [event for event in bus.history if event.type == "test.result"]
    assert len(results) == 1
    assert isinstance(results[0], ResultEvent)
    assert results[0].call_id == "call-1"
    assert (results[0].passed, results[0].failed, results[0].status) == (11, 1, "failed")
    # The persisted log carries the same event for replay.
    persisted = [
        json.loads(line) for line in (run_directory / "events.jsonl").read_text().splitlines()
    ]
    assert [event["type"] for event in persisted].count("test.result") == 1
