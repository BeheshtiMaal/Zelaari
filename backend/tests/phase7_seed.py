"""Seed the Phase 7 walkthrough: fixture projects, settings and one real compaction run.

The compaction is the product's own path — `.harness/config.json` says 30 %, the bridge builds
the summarizer from that setting, and the run leaves a summary file behind for the handoff.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

import agent.bridge as bridge
from agent.events import RunRequest
from agent.factory import build_agent
from providers.demo import DemoModel
from store.catalog import Catalog
from store.secrets import Redactor

SUMMARY = "Earlier work on the invoice parser: dates were parsed with a slash separator."

CONFIG = {
    "context": {
        "compaction_percent": 30,
        "keep_messages": 2,
        "offload": True,
        "show_ring": True,
    },
    "verify": {
        "gate": True,
        "command": None,
        "max_steps": 40,
        "max_minutes": 30,
        "fix_attempts": 3,
    },
    "terminal": {"shell": "auto", "timeout_seconds": 120, "max_output_lines": 200},
}

README = "# Invoice parser\n\nDates arrive as ISO text and are split into year, month and day.\n"

PYPROJECT = """[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
"""

FIXED = (
    "def parse_date(text):\n"
    '    year, month, day = (int(part) for part in text.split("-"))\n'
    "    return year, month, day\n"
)
BROKEN = 'def parse_date(text):\n    raise ValueError("unsupported format")\n'

# Eleven checks that never call the parser, plus one that does: the red project fails exactly
# one test, so the terminal shows a real mixed result and the fix loop has something to fix.
TESTS = '''import parser

VALUES = ["2026-10-24", "2024-01-02"]


def test_module_exposes_the_parser():
    assert callable(parser.parse_date)


def test_parser_module_name():
    assert parser.__name__ == "parser"


def test_sample_dates_are_iso():
    assert all(value.count("-") == 2 for value in VALUES)


def test_sample_dates_have_ten_characters():
    assert all(len(value) == 10 for value in VALUES)


def test_sample_years_are_modern():
    assert all(int(value[:4]) >= 2000 for value in VALUES)


def test_sample_months_are_valid():
    assert all(1 <= int(value[5:7]) <= 12 for value in VALUES)


def test_sample_days_are_valid():
    assert all(1 <= int(value[8:]) <= 31 for value in VALUES)


def test_values_are_unique():
    assert len(set(VALUES)) == len(VALUES)


def test_values_are_strings():
    assert all(isinstance(value, str) for value in VALUES)


def test_first_value_round_trips():
    assert VALUES[0] == "2026-10-24"


def test_second_value_round_trips():
    assert VALUES[1] == "2024-01-02"


def test_parses_iso_date():
    assert parser.parse_date("2026-10-24") == (2026, 10, 24)
'''


def project(root: Path, parser_source: str) -> None:
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(README, encoding="utf-8")
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (root / "parser.py").write_text(parser_source, encoding="utf-8")
    (root / "tests" / "test_parser.py").write_text(TESTS, encoding="utf-8")
    (root / ".harness").mkdir(parents=True, exist_ok=True)
    (root / ".harness" / "config.json").write_text(
        json.dumps(CONFIG, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class WindowedDemo(DemoModel):
    """Answers summarization calls, so the summary is a known string."""

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        # The summarizer calls the model without a system prompt; the agent always has one.
        if not any(isinstance(message, SystemMessage) for message in messages):
            return AIMessage(content=SUMMARY)
        return super().answer(messages)


class History(AgentMiddleware[Any, Any, Any]):
    async def abefore_agent(self, state: Any, runtime: Any) -> dict[str, Any]:
        messages: list[BaseMessage] = []
        for number in range(30):
            detail = f"observation {number} " + "invoice parser detail " * 22
            messages.extend(
                [
                    HumanMessage(content=f"Earlier local analysis {number}: {detail}"),
                    AIMessage(content=f"Earlier observed response {number}: {detail}"),
                ]
            )
        return {"messages": messages}


async def main() -> None:
    profile, workspace = Path(sys.argv[1]), Path(sys.argv[2])
    project(workspace, FIXED)
    if len(sys.argv) > 3:
        # The second fixture fails exactly one test, for the terminal and the fix loop.
        project(Path(sys.argv[3]), BROKEN)
    original = build_agent

    def factory(*args: Any, **kwargs: Any) -> Any:
        # A published window turns the configured percentage into a real token trigger.
        model = WindowedDemo(delay=0, profile={"max_input_tokens": 20_000})
        redactor = Redactor()
        args = (args[0], model, args[2], redactor)
        kwargs["extra_middleware"] = [*kwargs.get("extra_middleware", []), History()]
        return original(*args, **kwargs)

    setattr(bridge, "build_agent", factory)
    manager = bridge.RunManager(catalog=Catalog(profile / "catalog.json"), demo_delay=0)
    run_id = await manager.start(
        RunRequest(task="Seed the summary", workspace=str(workspace))
    )
    await manager.runs[run_id].task
    events = manager.runs[run_id].bus.history
    notices = [event for event in events if event.type == "context.summarized"]
    # The fixture window is 20K, so the system prompt and tool schemas are already a large
    # share of the 30 % trigger and this long run may compact more than once. Each notice is
    # a separate operation; the handoff only needs the last summary, which is what a new run
    # starts from.
    assert notices, "the run did not compact its history"
    path = workspace / ".harness" / "context" / "summaries" / f"{run_id}.md"
    assert path.exists(), "the summary file was not written"
    text = path.read_text(encoding="utf-8")
    assert SUMMARY in text, "the summary does not carry the model's summary"
    await manager.close()
    print(json.dumps({"run_id": run_id, "summary": str(path), "bytes": len(text.encode())}))


if __name__ == "__main__":
    asyncio.run(main())
