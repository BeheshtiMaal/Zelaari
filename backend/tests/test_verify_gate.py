"""The gate decides from tool results, survives a restart and never trusts the model."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.bridge import RunManager
from agent.events import RunRequest
from providers.verify_demo import verification_question
from questions.types import QuestionDecision, QuestionSelection
from store.catalog import Catalog
from store.secrets import Redactor
from tools.jail import storage_path
from verify.gate import MAX_INJECTIONS, decide, scan

COMMAND = "echo ok"


def edit(call_id: str = "edit-1", name: str = "write_file") -> AIMessage:
    return AIMessage(
        content="",
        id=f"ai-{call_id}",
        tool_calls=[
            {"name": name, "id": call_id, "args": {"file_path": "notes.txt", "content": "x"}}
        ],
    )


def result(
    call_id: str = "edit-1", *, status: str = "success", text: str = "Updated notes.txt"
) -> ToolMessage:
    return ToolMessage(
        content=text,
        tool_call_id=call_id,
        name="write_file",
        status=status,
    )


def command(
    call_id: str, value: str = COMMAND, exit_code: int = 0
) -> tuple[AIMessage, ToolMessage]:
    call = AIMessage(
        content="",
        id=f"ai-{call_id}",
        tool_calls=[{"name": "run_command", "id": call_id, "args": {"command": value}}],
    )
    payload = {
        "command": value,
        "shell": "powershell",
        "exit_code": exit_code,
        "duration_ms": 12,
        "output": "ok" if exit_code == 0 else "failed",
        "truncated": False,
        "total_lines": 1,
        "offset": 0,
        "timed_out": False,
        "timeout_seconds": 120,
        "killed_tree": False,
    }
    return call, ToolMessage(content=json.dumps(payload), tool_call_id=call_id, name="run_command")


def injected_message(index: int) -> HumanMessage:
    return HumanMessage(
        content="[harness] run the checks",
        name="harness",
        additional_kwargs={"harness": "verify", "index": index},
    )


def test_clean_finish_is_allowed() -> None:
    assert decide([HumanMessage(content="task")], COMMAND, True).action == "allow"


def test_edit_then_finish_is_blocked() -> None:
    messages = [HumanMessage(content="task"), edit(), result(), AIMessage(content="done")]
    decision = decide(messages, COMMAND, True)
    assert (decision.action, decision.reason) == ("block", "unverified_changes")
    assert decision.command == COMMAND


def test_passing_verification_allows_the_finish() -> None:
    call, outcome = command("run-1")
    messages = [
        HumanMessage(content="task"),
        edit(),
        result(),
        call,
        outcome,
        AIMessage(content="done"),
    ]
    assert decide(messages, COMMAND, True).action == "allow"


def test_failing_verification_does_not_satisfy_the_gate() -> None:
    call, outcome = command("run-1", exit_code=1)
    messages = [
        HumanMessage(content="task"),
        edit(),
        result(),
        call,
        outcome,
        AIMessage(content="done"),
    ]
    assert decide(messages, COMMAND, True).action == "block"


def test_other_command_does_not_satisfy_the_gate() -> None:
    call, outcome = command("run-1", value="git status", exit_code=0)
    messages = [HumanMessage(content="t"), edit(), result(), call, outcome, AIMessage(content="d")]
    assert decide(messages, COMMAND, True).action == "block"


def test_refused_or_failed_edit_is_not_a_change() -> None:
    refused = [
        HumanMessage(content="t"),
        edit(),
        result(status="error", text="Permission denied: write needs approval"),
        AIMessage(content="d"),
    ]
    assert decide(refused, COMMAND, True).action == "allow"
    errored = [
        HumanMessage(content="t"),
        edit(),
        result(text="Error: could not write notes.txt"),
        AIMessage(content="d"),
    ]
    assert decide(errored, COMMAND, True).action == "allow"


def test_edit_after_a_passing_check_needs_a_new_check() -> None:
    call, outcome = command("run-1")
    messages = [
        HumanMessage(content="t"),
        edit("edit-1"),
        result("edit-1"),
        call,
        outcome,
        edit("edit-2"),
        result("edit-2"),
        AIMessage(content="d"),
    ]
    assert decide(messages, COMMAND, True).action == "block"


def test_disabled_gate_allows_everything() -> None:
    messages = [HumanMessage(content="t"), edit(), result(), AIMessage(content="d")]
    assert decide(messages, COMMAND, False).action == "allow"


def test_gate_gives_up_after_three_injections() -> None:
    messages: list[Any] = [HumanMessage(content="t"), edit(), result()]
    for index in range(MAX_INJECTIONS):
        messages.append(AIMessage(content=f"done {index}"))
        messages.append(injected_message(index))
    messages.append(AIMessage(content="done"))
    decision = decide(messages, COMMAND, True)
    assert (decision.action, decision.reason) == ("give_up", "gave_up")


def test_a_passing_check_resets_the_injection_stretch() -> None:
    messages: list[Any] = [HumanMessage(content="t"), edit(), result()]
    for index in range(MAX_INJECTIONS - 1):
        messages.append(AIMessage(content=f"done {index}"))
        messages.append(injected_message(index))
    # One passing verification releases the stretch, so a later edit can be blocked again.
    call, outcome = command("pass-1")
    messages.extend([call, outcome, edit("edit-2"), result("edit-2"), AIMessage(content="done")])
    assert decide(messages, COMMAND, True).action == "block"


def test_no_command_asks_once_and_a_decline_turns_the_gate_off() -> None:
    messages: list[Any] = [HumanMessage(content="t"), edit(), result(), AIMessage(content="d")]
    assert decide(messages, None, True).action == "ask"
    question = AIMessage(
        content="",
        id="ai-q",
        tool_calls=[{"name": "ask_user_question", "id": "q-1", "args": verification_question()}],
    )
    declined = ToolMessage(
        content=json.dumps(
            {
                "kind": "question",
                "interrupt_id": "q-1",
                "status": "declined",
                "answers": [],
                "run_id": "run",
                "call_id": "q-1",
            }
        ),
        tool_call_id="q-1",
        name="ask_user_question",
    )
    decision = decide([*messages, question, declined], None, True)
    assert (decision.action, decision.reason) == ("allow", "declined")


def test_answered_verification_question_supplies_the_command() -> None:
    messages: list[Any] = [HumanMessage(content="t"), edit(), result()]
    question = AIMessage(
        content="",
        id="ai-q",
        tool_calls=[{"name": "ask_user_question", "id": "q-1", "args": verification_question()}],
    )
    answered = ToolMessage(
        content=json.dumps(
            {
                "kind": "question",
                "interrupt_id": "q-1",
                "status": "answered",
                "answers": [
                    {"question_id": "verify", "option_ids": [], "other": "python -m pytest"}
                ],
                "run_id": "run",
                "call_id": "q-1",
            }
        ),
        tool_call_id="q-1",
        name="ask_user_question",
    )
    decision = decide([*messages, question, answered], None, True)
    assert (decision.action, decision.command) == ("block", "python -m pytest")
    assert scan([*messages, question, answered], None).adopted == "python -m pytest"


def configure(root: Path, command: str) -> None:
    directory = storage_path(root, "")
    directory.mkdir(exist_ok=True)
    storage_path(root, "config.json").write_text(
        json.dumps(
            {
                "verify": {
                    "gate": True,
                    "command": command,
                    "max_steps": 40,
                    "max_minutes": 30,
                    "fix_attempts": 3,
                }
            }
        ),
        encoding="utf-8",
    )


def workspace(tmp_path: Path, command: str) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Fixture\n", encoding="utf-8")
    configure(project, command)
    return project


async def finished(manager: RunManager, run_id: str) -> None:
    async with asyncio.timeout(90):
        while not any(event.type == "run.finished" for event in manager.runs[run_id].bus.history):
            await asyncio.sleep(0.02)


def test_real_run_is_blocked_until_the_check_passes(tmp_path: Path) -> None:
    project = workspace(tmp_path, COMMAND)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify gate", workspace=str(project), mode="auto")
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    kinds = [event.type for event in events]
    assert "verify.required" in kinds
    blocked = next(event for event in events if event.type == "verify.required")
    assert blocked.blocked is True
    assert blocked.command == COMMAND
    assert kinds.count("test.result") == 1
    result = next(event for event in events if event.type == "test.result")
    assert (result.status, result.passed, result.failed) == ("passed", None, None)
    assert kinds[-1] == "run.finished"
    assert events[-1].status == "completed"
    # The injected instruction is harness text, never a new user task.
    assert (project / "notes.txt").read_text(encoding="utf-8") == "verified work\n"


def test_real_run_gives_up_when_the_check_keeps_failing(tmp_path: Path) -> None:
    project = workspace(tmp_path, "exit 1")

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify fail", workspace=str(project), mode="auto")
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    kinds = [event.type for event in events]
    assert kinds.count("verify.required") == MAX_INJECTIONS
    exhausted = [event for event in events if event.type == "budget.exhausted"]
    assert [(event.kind, event.limit) for event in exhausted] == [("verify", MAX_INJECTIONS)]
    assert events[-1].type == "run.finished"


def test_real_run_asks_for_a_command_and_adopts_it(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Fixture\n", encoding="utf-8")

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify question", workspace=str(project), mode="auto")
        )
        async with asyncio.timeout(60):
            while not manager.questions(run_id):
                await asyncio.sleep(0.02)
        record = manager.questions(run_id)[0]
        assert record.request.questions[0].header == "Verification"
        await manager.answer_question(
            run_id,
            record.request.call_id,
            QuestionDecision(
                interrupt_id=record.interrupt_id,
                status="answered",
                answers=[
                    QuestionSelection(question_id="verify", option_ids=[], other="echo adopted")
                ],
            ),
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    kinds = [event.type for event in events]
    assert kinds.count("verify.required") == 1
    first = next(event for event in events if event.type == "verify.required")
    assert (first.reason, first.command) == ("no_command", None)
    commands = [event.args.get("command") for event in events if event.type == "tool.call"]
    assert "echo adopted" in commands
    assert kinds.count("test.result") == 1
    assert events[-1].type == "run.finished"
    assert events[-1].status == "completed"


@pytest.mark.parametrize("mode", ["read-only"])
def test_read_only_runs_are_never_gated(tmp_path: Path, mode: str) -> None:
    project = workspace(tmp_path, COMMAND)

    async def scenario() -> list[Any]:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor()))
        run_id = await manager.start(
            RunRequest(task="demo verify gate", workspace=str(project), mode=mode)  # type: ignore[arg-type]
        )
        await finished(manager, run_id)
        await manager.close()
        return list(manager.runs[run_id].bus.history)

    events = asyncio.run(scenario())
    assert not any(event.type == "verify.required" for event in events)
