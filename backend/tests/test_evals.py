"""The eval suite is a fixture too: it must run offline, name cases uniquely, and report.

The full suite takes minutes, so this runs three cases rather than all twenty: enough to
prove the harness drives a real run on this machine. `python -m evals` runs the rest.
"""

from pathlib import Path

from evals.__main__ import run_all, summary, write_report
from evals.cases import CASES


def test_every_case_name_is_unique() -> None:
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))


def test_the_catalogue_covers_the_brief() -> None:
    areas = {case.area for case in CASES}
    required = {
        "jail",
        "commands",
        "plans",
        "verify",
        "approvals",
        "rules",
        "skills",
        "questions",
        "resume",
    }
    assert required <= areas, f"missing areas: {sorted(required - areas)}"
    assert len(CASES) >= 20, f"the brief asks for about twenty cases, found {len(CASES)}"


def test_three_cases_run_green_and_the_report_is_written(tmp_path: Path) -> None:
    rows = []
    for name in ("jail-parent", "approval-reject", "render-fallback"):
        rows += run_all(tmp_path, only=name, show_events=False)
    assert len(rows) == 3
    assert [row.result for row in rows] == ["pass", "pass", "pass"], [
        (row.name, row.detail) for row in rows if row.result != "pass"
    ]

    write_report(rows, tmp_path / "report.md")
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "| pass | jail | `jail-parent` |" in report
    assert "0 fail" in summary(rows)
    assert (tmp_path / "report.json").is_file()
