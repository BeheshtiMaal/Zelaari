"""Read pytest and npm-style output into counts a person can check.

Parsing is deliberately conservative: when the output does not state a number the
field stays `None`, so the UI shows the exit code instead of inventing a count.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_SUMMARY = 2000
MAX_FAILURES = 10
SUMMARY_LINES = 25

JEST = re.compile(r"Tests:\s*(?:(\d+) failed,\s*)?(?:(\d+) passed)?")
VITEST = re.compile(r"Tests\s+(?:(\d+) failed\s*\|\s*)?(\d+) passed")
MOCHA_PASSED = re.compile(r"(\d+) passing")
MOCHA_FAILED = re.compile(r"(\d+) failing")
PYTEST_PASSED = re.compile(r"(\d+) passed")
PYTEST_FAILED = re.compile(r"(\d+) failed")
PYTEST_ERRORS = re.compile(r"(\d+) errors?\b")
FAILURE_LINES = (
    re.compile(r"(?m)^\s*FAILED\s+(\S+)"),
    re.compile(r"(?m)^\s*ERROR\s+(\S+)"),
    re.compile(r"(?m)^\s*[●✕×]\s+(.+?)\s*$"),
    re.compile(r"(?m)^\s*\d+\)\s+(\S.*?)\s*$"),
)

Status = Literal["passed", "failed", "error", "timeout"]


class TestOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status
    exit_code: int | None
    passed: int | None = None
    failed: int | None = None
    duration_ms: int = Field(default=0, ge=0)
    failures: list[str] = Field(default_factory=list, max_length=MAX_FAILURES)
    summary: str = ""


def number(match: re.Match[str] | None, group: int = 1) -> int | None:
    if match is None:
        return None
    value = match.group(group)
    return int(value) if value is not None else None


def last(pattern: re.Pattern[str], text: str) -> int | None:
    """The final report line wins; earlier progress lines are noise."""
    found = pattern.findall(text)
    return int(found[-1]) if found else None


def counts(text: str) -> tuple[int | None, int | None]:
    jest = JEST.search(text)
    if jest is not None:
        return number(jest, 2), number(jest, 1)
    vitest = VITEST.search(text)
    if vitest is not None:
        return number(vitest, 2), number(vitest, 1)
    if MOCHA_PASSED.search(text) or MOCHA_FAILED.search(text):
        return last(MOCHA_PASSED, text), last(MOCHA_FAILED, text)
    passed, failed = last(PYTEST_PASSED, text), last(PYTEST_FAILED, text)
    errors = last(PYTEST_ERRORS, text)
    if errors is not None:
        # pytest reports collection/teardown errors apart from failures; both mean red.
        failed = (failed or 0) + errors
    return passed, failed


def failure_ids(text: str) -> list[str]:
    found: list[str] = []
    for pattern in FAILURE_LINES:
        for value in pattern.findall(text):
            item = value.strip()
            if item and item not in found:
                found.append(item)
            if len(found) >= MAX_FAILURES:
                return found
    return found


def excerpt(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    body = "\n".join(lines[-SUMMARY_LINES:])
    return body if len(body) <= MAX_SUMMARY else "…" + body[-MAX_SUMMARY:]


def parse_test_output(
    *,
    command: str,
    exit_code: int | None,
    timed_out: bool,
    duration_ms: int,
    output: str,
    redact: Callable[[str], str] | None = None,
) -> TestOutcome:
    """`command` is carried by the caller; every other field comes from real output."""
    scrub = redact or (lambda value: value)
    passed, failed = counts(output)
    if timed_out:
        status: Status = "timeout"
    elif exit_code is None:
        status = "error"
    elif exit_code == 0:
        status = "passed"
    else:
        status = "failed"
    return TestOutcome(
        status=status,
        exit_code=exit_code,
        passed=passed,
        failed=failed,
        duration_ms=max(0, duration_ms),
        failures=failure_ids(output),
        summary=scrub(excerpt(output)),
    )


def normalised(command: str) -> str:
    return " ".join(command.split()).casefold()


def matches_verification(command: str, verification: str) -> bool:
    """The configured command must have run as configured.

    A narrower run (`pytest -q tests/test_x.py`) or a collect-only run is not proof that
    the project's checks pass, so extra arguments do not count.
    """
    value, expected = normalised(command), normalised(verification)
    return bool(expected) and value == expected


@dataclass(frozen=True)
class RunOutcome:
    """What one `run_command` result actually reported."""

    exit_code: int | None
    output: str
    timed_out: bool


def run_outcome(content: str) -> RunOutcome | None:
    """Read a command result payload; `None` when the text is not one."""
    try:
        payload = json.loads(content)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    code = payload.get("exit_code")
    output = payload.get("output")
    return RunOutcome(
        exit_code=code if isinstance(code, int) else None,
        output=output if isinstance(output, str) else "",
        timed_out=bool(payload.get("timed_out")),
    )
