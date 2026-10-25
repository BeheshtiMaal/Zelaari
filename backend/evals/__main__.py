"""`python -m evals` — every case, a table, and a report file.

Exit code 1 if anything failed, so CI can gate on it. A skipped case is not a pass: it is
printed as `skip` with its reason, and the summary counts it separately.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from evals.cases import CASES
from evals.harness import Skipped, run_case


@dataclass(frozen=True)
class Row:
    name: str
    area: str
    result: str
    seconds: float
    events: int
    detail: str


def run_all(root: Path, only: str | None, show_events: bool) -> list[Row]:
    rows: list[Row] = []
    for case in CASES:
        if only and only not in case.name:
            continue
        started = time.monotonic()
        events = 0
        try:
            outcome = asyncio.run(run_case(case, root))
            events = len(outcome.events)
            if show_events:
                print(f"--- {case.name} ({outcome.status})")
                for event in outcome.events:
                    detail = str(getattr(event, "text", "") or getattr(event, "name", "") or "")[
                        :70
                    ]
                    print(f"    {event.type:22} {detail}")
            case.check(outcome)
            rows.append(
                Row(case.name, case.area, "pass", round(time.monotonic() - started, 2), events, "")
            )
        except Skipped as error:
            rows.append(
                Row(
                    case.name,
                    case.area,
                    "skip",
                    round(time.monotonic() - started, 2),
                    events,
                    str(error),
                )
            )
        except AssertionError as error:
            rows.append(
                Row(
                    case.name,
                    case.area,
                    "fail",
                    round(time.monotonic() - started, 2),
                    events,
                    str(error) or "assertion failed",
                )
            )
        except (
            Exception
        ) as error:  # a crashing case is a result to report, not a traceback to print
            rows.append(
                Row(
                    case.name,
                    case.area,
                    "error",
                    round(time.monotonic() - started, 2),
                    events,
                    f"{type(error).__name__}: {error}",
                )
            )
    return rows


def table(rows: list[Row]) -> str:
    width = max((len(row.name) for row in rows), default=4)
    lines = [f"{'result':6} {'area':10} {'case':{width}}  {'s':>5}  detail"]
    for row in rows:
        lines.append(
            f"{row.result:6} {row.area:10} {row.name:{width}}  "
            f"{row.seconds:5.1f}  {row.detail[:110]}"
        )
    return "\n".join(lines)


def summary(rows: list[Row]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.result] = counts.get(row.result, 0) + 1
    parts = [f"{counts.get(name, 0)} {name}" for name in ("pass", "fail", "error", "skip")]
    return f"{len(rows)} cases: " + ", ".join(parts)


def write_report(rows: list[Row], target: Path) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.result] = counts.get(row.result, 0) + 1
    lines = [
        "# Eval report",
        "",
        f"{summary(rows)}",
        "",
        "| result | area | case | seconds | detail |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.result} | {row.area} | `{row.name}` | {row.seconds:.1f} | {row.detail or ''} |"
        )
    lines += [
        "",
        "A `skip` is a case this machine could not run, and it is never counted as a pass.",
        "The live-model half is `evals/live-checklist.md`: CI has no key and must not.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    (target.parent / "report.json").write_text(
        json.dumps({"counts": counts, "cases": [asdict(row) for row in rows]}, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic eval suite.")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--only", default=None, help="run cases whose name contains this")
    parser.add_argument("--events", action="store_true", help="print each case's event stream")
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="codeharness-evals-") as directory:
        rows = run_all(Path(directory), arguments.only, arguments.events)
    print(table(rows))
    print()
    print(summary(rows))
    write_report(rows, arguments.out / "report.md")
    print(f"report: {arguments.out / 'report.md'}")
    return 1 if any(row.result in {"fail", "error"} for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
