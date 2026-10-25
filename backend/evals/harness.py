"""One real run per case, through the engine the app itself uses.

D46: a case drives a real `RunManager` and reads the events it wrote. A suite that
reimplemented the loop would keep passing after the product broke.

A case says what to ask, what the workspace holds, and how to answer whatever the run asks
back. Everything else — starting, settling, stopping — is here, once.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeVar
from unittest import mock

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

from agent.bridge import RunManager
from agent.events import Event, RunFinished, RunRequest
from permissions.types import ApprovalDecision, ApprovalRecord
from questions.types import QuestionDecision, QuestionRecord, QuestionSelection
from store.catalog import Catalog

EventT = TypeVar("EventT", bound=Event)

FINAL = AIMessage(content='root = Callout("done");')
"""A terminating turn: no tool calls, so the graph stops."""

SETTLE_TIMEOUT = 240.0
"""One run may wait on a verify command; this is the ceiling, not the expectation."""


class Skipped(Exception):
    """This machine cannot run the case. Reported as skipped, never as passed."""


class ScriptedModel(BaseChatModel):
    """Replays one assistant turn per model call, repeating the last."""

    replies: list[AIMessage]
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "eval-scripted"

    def bind_tools(
        self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any
    ) -> Runnable[Any, Any]:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=reply)])


@dataclass(frozen=True)
class Answers:
    """How a case answers what the run asks. `leave` keeps it pending on purpose.

    A run may ask more than once (a plan, then a command). Give a tuple to answer the rounds
    in order; the last policy repeats. A single string is shorthand for one policy.
    """

    approvals: str | tuple[str, ...] = "leave"
    questions: Literal["leave", "answer", "decline"] = "leave"
    edited_args: Mapping[str, Any] = field(default_factory=dict)
    allow_glob: str = "**"

    def policy(self, round_index: int) -> str:
        steps = (self.approvals,) if isinstance(self.approvals, str) else self.approvals
        return steps[min(round_index, len(steps) - 1)]


@dataclass(frozen=True)
class Outcome:
    """Everything a case is allowed to assert on."""

    name: str
    run_id: str
    status: str
    events: tuple[Event, ...]
    approvals: tuple[ApprovalRecord, ...]
    questions: tuple[QuestionRecord, ...]
    catalog: Catalog
    catalog_path: Path
    workspace: Path

    def of(self, kind: type[EventT]) -> list[EventT]:
        return [event for event in self.events if isinstance(event, kind)]

    def types(self) -> list[str]:
        return [event.type for event in self.events]

    def spoken(self) -> str:
        """Every piece of text the run produced, for "never appears" assertions."""
        parts: list[str] = []
        for event in self.events:
            parts.append(str(getattr(event, "text", "")))
            parts.append(str(getattr(event, "task", "")))
            request = getattr(event, "request", None)
            if request is not None:
                parts.append(str(getattr(request, "command", "") or ""))
                parts.append(str(getattr(request, "path", "") or ""))
        return "\n".join(parts)

    def tool_results(self) -> list[str]:
        return [
            str(getattr(event, "text", "")) for event in self.events if event.type == "tool.result"
        ]


@dataclass(frozen=True)
class Case:
    name: str
    area: str
    task: str
    check: Callable[[Outcome], None]
    files: Mapping[str, str] = field(default_factory=dict)
    outside: Mapping[str, str] = field(default_factory=dict)
    """Files beside the workspace, for the cases that try to leave it."""
    mode: Literal["read-only", "ask", "auto"] = "ask"
    script: Sequence[AIMessage] | None = None
    answers: Answers = field(default_factory=Answers)
    setup: Callable[[Path], None] | None = None


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _finished(manager: RunManager, run_id: str) -> str | None:
    run = manager.runs.get(run_id)
    if run is None:
        return None
    for event in reversed(run.bus.history):
        if isinstance(event, RunFinished):
            return event.status
    return None


def _pending_approvals(manager: RunManager, run_id: str) -> list[ApprovalRecord]:
    return [record for record in manager.approvals("pending") if record.request.run_id == run_id]


def _pending_questions(manager: RunManager, run_id: str) -> list[QuestionRecord]:
    return [record for record in manager.questions(run_id) if record.status == "pending"]


async def _wait(manager: RunManager, run_id: str) -> None:
    """Block until the run finishes or asks something. Polling, because both are pushes."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + SETTLE_TIMEOUT
    while True:
        if _finished(manager, run_id) is not None:
            return
        if _pending_approvals(manager, run_id) or _pending_questions(manager, run_id):
            return
        if loop.time() > deadline:
            raise TimeoutError(f"{run_id} neither finished nor asked anything in {SETTLE_TIMEOUT}s")
        await asyncio.sleep(0.02)


def _approval_decision(policy: str, answers: Answers) -> ApprovalDecision:
    if policy == "reject":
        return ApprovalDecision(decision="reject", reason="rejected by the eval")
    if policy == "edit":
        return ApprovalDecision(decision="approve", edited_args=dict(answers.edited_args))
    if policy == "allow":
        return ApprovalDecision(decision="approve", allow_glob=answers.allow_glob)
    return ApprovalDecision(decision="approve")


def _question_decision(record: QuestionRecord, answers: Answers) -> QuestionDecision:
    if answers.questions == "decline":
        return QuestionDecision(interrupt_id=record.interrupt_id, status="declined")
    selections: list[QuestionSelection] = []
    for question in record.request.questions:
        offered = [option.id for option in question.options]
        chosen = offered if question.type == "rank" else offered[:1]
        selections.append(QuestionSelection(question_id=question.id, option_ids=chosen))
    return QuestionDecision(interrupt_id=record.interrupt_id, status="answered", answers=selections)


async def _settle(manager: RunManager, run_id: str, answers: Answers) -> str:
    """Answer what the case asked us to answer, then report how the run ended."""
    round_index = 0
    for _ in range(32):
        await _wait(manager, run_id)
        finished = _finished(manager, run_id)
        if finished is not None:
            return finished
        approvals = _pending_approvals(manager, run_id)
        if approvals:
            policy = answers.policy(round_index)
            if policy == "leave":
                return "pending"
            decision = _approval_decision(policy, answers)
            approval_id = approvals[0].request.approval_id
            if policy == "edit":
                # The engine refuses edited arguments that were never previewed: a person
                # has to see what they are about to approve.
                manager.preview(run_id, approval_id, decision)
            await manager.resolve(run_id, approval_id, decision)
            round_index += 1
            await asyncio.sleep(0.05)
            continue
        questions = _pending_questions(manager, run_id)
        if questions:
            if answers.questions == "leave":
                return "pending"
            await manager.answer_question(
                run_id, questions[0].request.call_id, _question_decision(questions[0], answers)
            )
            await asyncio.sleep(0.05)
            continue
        return "pending"
    raise TimeoutError(f"{run_id} kept asking after 32 rounds")


async def run_case(case: Case, root: Path) -> Outcome:
    """One case, one workspace, one real manager, one run."""
    home = root / case.name
    workspace = home / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    for name, content in case.files.items():
        _write(workspace / name, content)
    for name, content in case.outside.items():
        _write(home / name, content)
    if case.setup is not None:
        case.setup(workspace)

    catalog = Catalog(home / "catalog.json")
    manager = RunManager(catalog=catalog, demo_delay=0.0)
    scripted = ScriptedModel(replies=list(case.script)) if case.script else None
    patcher: Any = (
        mock.patch("agent.bridge.DemoModel", lambda **_kwargs: scripted)
        if scripted is not None
        else contextlib.nullcontext()
    )
    try:
        with patcher:
            request = RunRequest(
                task=case.task.format(home=home), workspace=str(workspace), mode=case.mode
            )
            run_id = await manager.start(request)
            status = await _settle(manager, run_id, case.answers)
        run = manager.runs.get(run_id)
        events: tuple[Event, ...] = tuple(run.bus.history) if run is not None else ()
        return Outcome(
            name=case.name,
            run_id=run_id,
            status=status,
            events=events,
            approvals=tuple(manager.approvals()),
            questions=tuple(manager.questions(run_id)),
            catalog=catalog,
            catalog_path=home / "catalog.json",
            workspace=workspace,
        )
    finally:
        await manager.close()
