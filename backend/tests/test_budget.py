"""Budgets and the reflect loop: counters come from history, never from prose."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.bridge import RunManager
from agent.events import RunRequest
from questions.types import QuestionDecision, QuestionSelection
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor
from tools.jail import storage_path
from verify.budget import (
    MARK,
    BudgetMiddleware,
    Reflection,
    Usage,
    choice_of,
    exhausted_answer,
    limit_of,
    reached,
    reflect,
    steps_used,
    usage_of,
)
from verify.gate import VerifyGateMiddleware
from verify.settings import VerifySettings

COMMAND = "pytest -q"
FIXTURE = """from parser import parse_date


def test_jalali_date():
    assert parse_date("1403-05-12") == (1403, 5, 12)
"""


def answer(
    content: str = "", *, command: str = COMMAND, code: int = 1, identifier: str = "run"
) -> ToolMessage:
    payload = {
        "command": command,
        "shell": "powershell",
        "exit_code": code,
        "duration_ms": 10,
        "output": content or ("1 failed" if code else "1 passed"),
        "truncated": False,
        "total_lines": 1,
        "offset": 0,
        "timed_out": False,
        "timeout_seconds": 120,
        "killed_tree": False,
    }
    return ToolMessage(content=json.dumps(payload), tool_call_id=identifier, name="run_command")


def run_call(identifier: str = "run") -> AIMessage:
    return AIMessage(
        content="",
        id=f"ai-{identifier}",
        tool_calls=[{"name": "run_command", "id": identifier, "args": {"command": COMMAND}}],
    )


def failed_run(identifier: str = "run") -> list[Any]:
    return [run_call(identifier), answer(identifier=identifier)]


def card(options: list[str], *, hint: str | None = None) -> list[Any]:
    """One exhausted question and its answer, as the barrier records them."""
    question = AIMessage(
        content="",
        id="ai-ask",
        tool_calls=[
            {
                "name": "ask_user_question",
                "id": "ask-1",
                "args": {
                    "presentation": "exhausted",
                    "questions": [{"id": "exhausted", "header": "Recovery", "text": "Now what?"}],
                    "failure": {"attempts": 3, "step": "fix", "check": COMMAND, "output": ""},
                },
            }
        ],
    )
    selection: dict[str, Any] = {"question_id": "exhausted", "option_ids": options}
    if hint:
        selection["hint"] = hint
    replied = ToolMessage(
        content=json.dumps(
            {
                "kind": "question",
                "interrupt_id": "ask-1",
                "status": "answered",
                "answers": [selection],
                "run_id": "run",
                "call_id": "ask-1",
            }
        ),
        tool_call_id="ask-1",
        name="ask_user_question",
    )
    return [question, replied]


def declined_card() -> list[Any]:
    question = AIMessage(
        content="",
        id="ai-ask",
        tool_calls=[
            {
                "name": "ask_user_question",
                "id": "ask-1",
                "args": {"presentation": "exhausted", "questions": []},
            }
        ],
    )
    replied = ToolMessage(
        content=json.dumps(
            {
                "kind": "question",
                "interrupt_id": "ask-1",
                "status": "declined",
                "answers": [],
                "run_id": "run",
                "call_id": "ask-1",
            }
        ),
        tool_call_id="ask-1",
        name="ask_user_question",
    )
    return [question, replied]


def instruction(kind: str) -> HumanMessage:
    return HumanMessage(
        content=f"[harness] {kind}",
        name="harness",
        additional_kwargs={"harness": MARK, "kind": kind},
    )


def settings(**values: Any) -> VerifySettings:
    return VerifySettings.model_validate(
        {"gate": True, "command": COMMAND, "max_steps": 40, "max_minutes": 30, "fix_attempts": 3}
        | values
    )


def test_a_step_is_a_model_turn_that_asks_for_tools() -> None:
    messages = [
        HumanMessage(content="task"),
        AIMessage(content="thinking"),
        run_call(),
        answer(),
        AIMessage(content="done"),
    ]
    assert steps_used(messages) == 1


def test_only_failed_runs_of_the_verification_command_are_attempts() -> None:
    assert reflect([*failed_run()], COMMAND).attempts == 1
    assert reflect([*failed_run()], None).attempts == 0
    other = [
        AIMessage(
            content="",
            id="ai-other",
            tool_calls=[{"name": "run_command", "id": "other", "args": {"command": "git status"}}],
        ),
        ToolMessage(
            content=json.dumps({"command": "git status", "exit_code": 1}),
            tool_call_id="other",
            name="run_command",
        ),
    ]
    assert reflect(other, COMMAND).attempts == 0
    passed = [run_call(), answer(code=0)]
    assert reflect(passed, COMMAND).attempts == 0


def test_a_passing_run_clears_the_stretch() -> None:
    messages: list[Any] = []
    for index in range(3):
        messages.extend(failed_run(f"run-{index}"))
    assert reflect(messages, COMMAND).attempts == 3
    messages.extend([run_call("pass"), answer(code=0, identifier="pass")])
    assert reflect(messages, COMMAND).attempts == 0


def test_the_answer_is_read_from_the_recorded_card() -> None:
    found = reflect([*failed_run(), *card(["retry"], hint="split on the dash")], COMMAND)
    assert (found.option, found.hint, found.attempts) == ("retry", "split on the dash", 0)


def test_a_declined_card_reads_as_stop() -> None:
    found = reflect([*failed_run(), *declined_card()], COMMAND)
    assert (found.option, found.stopped) == ("declined", True)
    assert choice_of(found, 3) == "stop"


def test_typed_guidance_counts_as_a_retry() -> None:
    messages = [*failed_run()]
    question, replied = card(["retry"])
    selection = json.loads(str(replied.content))
    selection["answers"][0] = {"question_id": "exhausted", "option_ids": [], "other": "use a regex"}
    messages.extend(
        [
            question,
            ToolMessage(
                content=json.dumps(selection), tool_call_id="ask-1", name="ask_user_question"
            ),
        ]
    )
    found = reflect(messages, COMMAND)
    assert (found.option, found.hint) == ("retry", "use a regex")


def test_the_card_is_asked_once_per_stretch() -> None:
    found = Reflection(attempts=3)
    assert choice_of(found, 3) == "ask"
    asked = Reflection(attempts=3, asked=True)
    assert choice_of(asked, 3) is None
    assert choice_of(Reflection(attempts=2), 3) is None
    assert choice_of(Reflection(attempts=3), 0) is None


def test_an_injected_instruction_marks_the_round() -> None:
    messages: list[Any] = [*failed_run(), instruction("ask")]
    assert reflect(messages, COMMAND).asked is True
    messages.append(instruction("retry"))
    found = reflect(messages, COMMAND)
    assert (found.asked, found.handled) == (True, True)


def test_every_answer_choice_is_acted_on_once() -> None:
    assert choice_of(Reflection(option="retry", hint="h"), 3) == "retry"
    assert choice_of(Reflection(option="change"), 3) == "change"
    assert choice_of(Reflection(option="stop"), 3) == "stop"
    handled = Reflection(option="retry", hint="h", handled=True)
    assert choice_of(handled, 3) is None


def test_caps_are_read_from_the_settings() -> None:
    usage = usage_of([run_call(), answer()], COMMAND, settings(max_minutes=2), 1500)
    assert (usage.max_seconds, usage.fix_attempts, usage.elapsed_ms) == (120, 1, 1500)
    assert limit_of(usage, "time") == 120
    assert limit_of(usage, "steps") == 40


def counted(steps: int = 1, *, elapsed: int = 10) -> Usage:
    return Usage(
        steps=steps,
        fix_attempts=0,
        elapsed_ms=elapsed,
        max_steps=40,
        max_seconds=60,
        max_fix_attempts=3,
    )


def test_steps_come_before_time() -> None:
    assert reached(replace(counted(4), max_steps=4, elapsed_ms=10**9)) == "steps"
    assert reached(counted(1, elapsed=60_000)) == "time"
    assert reached(counted()) is None


def test_exhausted_answer_ignores_unrelated_results() -> None:
    plain = ToolMessage(content="done", tool_call_id="x", name="write_file")
    assert exhausted_answer(plain) == (False, None, None)


def configure(root: Path, command: str, **values: Any) -> None:
    directory = storage_path(root, "")
    directory.mkdir(exist_ok=True)
    payload = {
        "gate": True,
        "command": command,
        "max_steps": 40,
        "max_minutes": 30,
        "fix_attempts": 3,
    } | values
    storage_path(root, "config.json").write_text(json.dumps({"verify": payload}), encoding="utf-8")


def project(tmp_path: Path, **values: Any) -> Path:
    root = tmp_path / "project"
    (root / "tests").mkdir(parents=True)
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "tests" / "test_parser.py").write_text(FIXTURE, encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\npythonpath = .\n", encoding="utf-8")
    configure(root, COMMAND, **values)
    return root


async def finished(manager: RunManager, run_id: str) -> None:
    async with asyncio.timeout(120):
        while not any(event.type == "run.finished" for event in manager.runs[run_id].bus.history):
            await asyncio.sleep(0.02)


async def until_question(manager: RunManager, run_id: str) -> Any:
    async with asyncio.timeout(120):
        while not manager.questions(run_id):
            await asyncio.sleep(0.02)
    return manager.questions(run_id)[0]


def test_real_run_raises_the_exhausted_card_and_a_hint_turns_the_check_green(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify budget", workspace=str(root), mode="auto")
        )
        record = await until_question(manager, run_id)
        assert record.request.presentation == "exhausted"
        assert record.request.failure is not None
        assert record.request.failure.attempts == 3
        assert {option.id for option in record.request.questions[0].options} == {
            "retry",
            "change",
            "stop",
        }
        await manager.answer_question(
            run_id,
            record.request.call_id,
            QuestionDecision(
                interrupt_id=record.interrupt_id,
                status="answered",
                answers=[
                    QuestionSelection(
                        question_id="exhausted",
                        option_ids=["retry"],
                        hint="split on the dash and convert",
                    )
                ],
            ),
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    kinds = [event.type for event in events]
    assert kinds.count("test.result") == 4
    results = [event.status for event in events if event.type == "test.result"]
    assert results == ["failed", "failed", "failed", "passed"]
    assert events[-1].type == "run.finished"
    assert events[-1].status == "completed"
    written = (root / "parser.py").read_text(encoding="utf-8")
    assert "guidance: split on the dash and convert" in written
    # The counter is visible and resets on retry instead of hiding the reset.
    fix = [event.fix_attempts for event in events if event.type == "budget.updated"]
    assert max(fix) == 3
    assert fix[-1] == 0


def test_real_run_stops_on_the_step_cap(tmp_path: Path) -> None:
    root = project(tmp_path, max_steps=4)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify budget", workspace=str(root), mode="auto")
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    exhausted = [event for event in events if event.type == "budget.exhausted"]
    assert [(event.kind, event.limit) for event in exhausted] == [("steps", 4)]
    assert events[-1].type == "run.finished"
    assert events[-1].status == "stopped"
    # Approved changes stay on disk even when the run is cut short.
    assert (root / "parser.py").exists()


def test_real_run_requires_a_plan_revision_after_change(tmp_path: Path) -> None:
    root = project(tmp_path)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify budget", workspace=str(root), mode="auto")
        )
        record = await until_question(manager, run_id)
        await manager.answer_question(
            run_id,
            record.request.call_id,
            QuestionDecision(
                interrupt_id=record.interrupt_id,
                status="answered",
                answers=[QuestionSelection(question_id="exhausted", option_ids=["change"])],
            ),
        )
        history = manager.runs[run_id].bus.history
        async with asyncio.timeout(120):
            while len([event for event in history if _plan(event)]) < 2:
                await asyncio.sleep(0.02)
                if any(event.type == "run.finished" for event in history):
                    break
        await manager.stop(run_id)
        await finished(manager, run_id)
        await manager.close()
        return list(history)

    events = asyncio.run(scenario())
    plans = [event for event in events if _plan(event)]
    assert len(plans) == 2
    assert [step["id"] for step in plans[-1].args["steps"]] == ["retry"]
    assert "guidance:" not in (root / "parser.py").read_text(encoding="utf-8")


def _plan(event: Any) -> bool:
    return bool(event.type == "tool.call" and event.name == "submit_plan")


def test_a_declined_card_finishes_with_the_gate_suspended(tmp_path: Path) -> None:
    root = project(tmp_path)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify budget", workspace=str(root), mode="auto")
        )
        record = await until_question(manager, run_id)
        await manager.answer_question(
            run_id,
            record.request.call_id,
            QuestionDecision(interrupt_id=record.interrupt_id, status="declined"),
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    assert events[-1].type == "run.finished"
    assert events[-1].status == "completed"
    assert not any(
        event.type == "verify.required" and event.reason == "unverified_changes" for event in events
    )


def test_the_clock_cap_stops_the_run(tmp_path: Path) -> None:
    async def scenario() -> tuple[list[bool], EventBus]:
        bus = EventBus(tmp_path / "events.jsonl", "run", Redactor())
        started = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
        await bus.emit("run.started", task="task", model="demo")
        # A restored run: the clock starts at the run's first event, not at this process.
        bus.history[0].ts = started - timedelta(minutes=31)
        stopped: list[bool] = []
        gate = VerifyGateMiddleware(bus, COMMAND)
        budget = BudgetMiddleware(
            bus, settings(max_minutes=30), COMMAND, gate=gate, stop=lambda: stopped.append(True)
        )
        state = {"messages": [HumanMessage(content="task"), run_call(), answer()]}
        await budget.abefore_model(state, None)  # type: ignore[arg-type]
        # Announced once, not on every turn after the cap.
        await budget.abefore_model(state, None)  # type: ignore[arg-type]
        return stopped, bus

    stopped, bus = asyncio.run(scenario())
    assert stopped == [True]
    exhausted = [event for event in bus.history if event.type == "budget.exhausted"]
    assert [(event.kind, event.limit) for event in exhausted] == [("time", 1800)]
