"""The permission gate: allow, deny, ask/resume, and the fail-closed paths.

These drive a real deepagents graph with a scripted model, so the middleware is
exercised through the same nodes, checkpoint and interrupt machinery the product uses.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.bridge import Run, RunManager
from agent.events import Event, RunRequest
from agent.factory import build_agent
from permissions.middleware import PermissionMiddleware, tool_target
from permissions.rules import RulesEngine
from permissions.types import (
    ApprovalDecision,
    ApprovalRequest,
    Mode,
    UnknownApproval,
)
from server.app import create_app
from store.eventlog import EventBus
from store.secrets import Redactor
from tools.command import CommandRunner, build_run_command
from tools.jail import BLOCK_NOTE, jail_message, storage_path

FINAL = AIMessage(content='root = Callout("done");')
"""A terminating assistant turn: no tool calls, so the graph stops."""


class ScriptedModel(BaseChatModel):
    """Replays one scripted assistant turn per model call, repeating the last."""

    replies: list[AIMessage]
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(
        self,
        tools: Any,
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
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


def call(name: str, args: dict[str, Any], call_id: str = "c1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / ".harness").mkdir()
    return tmp_path


def build(
    root: Path,
    mode: Mode,
    replies: list[AIMessage],
    *,
    commands: bool = False,
) -> tuple[Any, dict[str, Any]]:
    tools = [build_run_command(CommandRunner(root, Redactor([])))] if commands else []
    graph = build_agent(
        root,
        ScriptedModel(replies=replies),
        cast(AsyncSqliteSaver, InMemorySaver()),
        Redactor([]),
        permissions=PermissionMiddleware(RulesEngine.load(root, mode), run_id="run-1"),
        extra_tools=tools,
    )
    return graph, {"configurable": {"thread_id": "thread-1"}}


def run_graph(graph: Any, config: dict[str, Any], task: str = "do the thing") -> dict[str, Any]:
    return cast(
        dict[str, Any],
        asyncio.run(graph.ainvoke({"messages": [{"role": "user", "content": task}]}, config)),
    )


def tool_results(state: dict[str, Any]) -> list[ToolMessage]:
    return [item for item in state["messages"] if isinstance(item, ToolMessage)]


def approvals(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [item.value for item in state.get("__interrupt__", ())]


# -- allow -----------------------------------------------------------------
def test_allow_executes_the_tool(root: Path) -> None:
    graph, config = build(
        root,
        "auto",
        [call("write_file", {"file_path": "a.txt", "content": "hello"}), FINAL],
    )
    state = run_graph(graph, config)

    assert (root / "a.txt").read_text(encoding="utf-8") == "hello"
    assert "__interrupt__" not in state
    assert state["messages"][-1].content == FINAL.content


def test_internal_tools_are_not_gated_even_in_read_only(root: Path) -> None:
    graph, config = build(
        root,
        "read-only",
        [call("write_todos", {"todos": [{"content": "look", "status": "pending"}]}), FINAL],
    )
    state = run_graph(graph, config)

    assert "__interrupt__" not in state
    results = tool_results(state)
    assert results and "Permission denied" not in str(results[0].content)


# -- deny ------------------------------------------------------------------
@pytest.mark.parametrize("path", [r"C:\Users\fixture\.ssh\id_rsa", "../outside/secret.txt"])
def test_graph_returns_the_jail_card_sentence_and_continues(root: Path, path: str) -> None:
    graph, config = build(root, "ask", [call("read_file", {"file_path": path}), FINAL])
    state = run_graph(graph, config)
    result = tool_results(state)[0]
    assert result.content == jail_message(root, path)
    assert BLOCK_NOTE in str(result.content)
    assert "__interrupt__" not in state
    assert state["messages"][-1].content == FINAL.content


def test_deny_returns_a_readable_error_and_the_run_continues(root: Path) -> None:
    graph, config = build(
        root,
        "read-only",
        [call("write_file", {"file_path": "a.txt", "content": "hello"}), FINAL],
    )
    state = run_graph(graph, config)

    assert not (root / "a.txt").exists()
    results = tool_results(state)
    assert len(results) == 1
    assert "Permission denied" in str(results[0].content)
    assert "read-only mode blocks write" in str(results[0].content)
    assert results[0].tool_call_id == "c1"
    # The model still produced its closing turn: a denial is not a run failure.
    assert state["messages"][-1].content == FINAL.content


def test_read_only_denies_a_command_without_running_it(root: Path) -> None:
    graph, config = build(
        root,
        "read-only",
        [call("run_command", {"command": "Set-Content -Path proof.txt -Value ran"}), FINAL],
        commands=True,
    )
    state = run_graph(graph, config)

    assert not (root / "proof.txt").exists(), "the command ran despite the denial"
    assert "Permission denied" in str(tool_results(state)[0].content)


# -- ask, then resume ------------------------------------------------------
def test_ask_interrupts_then_approve_writes(root: Path) -> None:
    graph, config = build(
        root,
        "ask",
        [call("write_file", {"file_path": "a.txt", "content": "hello"}), FINAL],
    )
    paused = run_graph(graph, config)

    pending = approvals(paused)
    assert len(pending) == 1
    assert pending[0]["approval_id"] == "c1"
    assert pending[0]["tool"] == "write_file"
    assert pending[0]["path"] == "a.txt"
    assert pending[0]["kind"] == "tool"
    assert not (root / "a.txt").exists(), "the tool ran before the decision"

    state = cast(
        dict[str, Any],
        asyncio.run(
            graph.ainvoke(
                Command(resume={"approval_id": "c1", "decision": "approve"}),
                config,
            )
        ),
    )

    assert (root / "a.txt").read_text(encoding="utf-8") == "hello"
    assert state["messages"][-1].content == FINAL.content


def test_ask_then_reject_feeds_the_reason_back(root: Path) -> None:
    graph, config = build(
        root,
        "ask",
        [call("write_file", {"file_path": "a.txt", "content": "hello"}), FINAL],
    )
    run_graph(graph, config)
    state = cast(
        dict[str, Any],
        asyncio.run(
            graph.ainvoke(
                Command(
                    resume={
                        "approval_id": "c1",
                        "decision": "reject",
                        "reason": "keep the file untouched",
                    }
                ),
                config,
            )
        ),
    )

    assert not (root / "a.txt").exists()
    result = str(tool_results(state)[0].content)
    assert "rejected by the user" in result
    assert "keep the file untouched" in result
    assert state["messages"][-1].content == FINAL.content


def test_approval_id_must_match_the_pending_call(root: Path) -> None:
    graph, config = build(
        root,
        "ask",
        [call("write_file", {"file_path": "a.txt", "content": "hello"}), FINAL],
    )
    run_graph(graph, config)
    state = cast(
        dict[str, Any],
        asyncio.run(
            graph.ainvoke(
                Command(resume={"approval_id": "other", "decision": "approve"}),
                config,
            )
        ),
    )

    assert not (root / "a.txt").exists()
    assert "did not match this call" in str(tool_results(state)[0].content)


# -- always-ask survives auto ---------------------------------------------
def test_auto_still_asks_before_writing_the_rules_file(root: Path) -> None:
    graph, config = build(
        root,
        "auto",
        [
            call("write_file", {"file_path": ".harness/rules.json", "content": "{}"}),
            FINAL,
        ],
    )
    paused = run_graph(graph, config)

    pending = approvals(paused)
    assert len(pending) == 1
    assert "engine storage always needs approval" in pending[0]["reason"]
    assert not (root / ".harness" / "rules.json").exists()


def test_auto_still_asks_before_a_high_risk_command(root: Path) -> None:
    graph, config = build(
        root,
        "auto",
        [call("run_command", {"command": "Remove-Item -Recurse -Force ."}), FINAL],
        commands=True,
    )
    paused = run_graph(graph, config)

    pending = approvals(paused)
    assert len(pending) == 1
    assert pending[0]["kind"] == "command"
    assert pending[0]["command"] == "Remove-Item -Recurse -Force ."
    assert pending[0]["risk"]["level"] == "high"
    assert pending[0]["risk"]["reasons"]


def test_auto_does_not_ask_for_a_plain_command(root: Path) -> None:
    graph, config = build(
        root,
        "auto",
        [call("run_command", {"command": "Write-Output ok"}), FINAL],
        commands=True,
    )
    state = run_graph(graph, config)

    assert "__interrupt__" not in state
    assert "ok" in str(tool_results(state)[0].content)


def test_a_longer_timeout_asks_even_in_auto(root: Path) -> None:
    graph, config = build(
        root,
        "auto",
        [call("run_command", {"command": "Write-Output ok", "timeout": 300}), FINAL],
        commands=True,
    )
    paused = run_graph(graph, config)

    pending = approvals(paused)
    assert len(pending) == 1
    assert "timeout above 120s" in pending[0]["reason"]
    assert "Requested timeout: 300s" in pending[0]["reason"]


# -- target extraction -----------------------------------------------------
@pytest.mark.parametrize(
    ("tool", "args", "expected"),
    [
        ("read_file", {"file_path": "a.txt"}, ("a.txt", None, None)),
        ("write_file", {"file_path": "a.txt", "content": "x"}, ("a.txt", None, None)),
        ("delete", {"file_path": "a.txt"}, ("a.txt", None, None)),
        ("ls", {"path": "src"}, ("src", None, None)),
        ("grep", {"pattern": "x", "path": "src"}, ("src", None, None)),
        ("run_command", {"command": "ls", "timeout": 30}, (None, "ls", 30.0)),
        ("git_switch", {"branch": "main"}, (None, "git switch main", None)),
        ("web_search", {"query": "x"}, (None, None, None)),
    ],
)
def test_tool_target_extraction(
    tool: str, args: dict[str, Any], expected: tuple[str | None, str | None, float | None]
) -> None:
    assert tool_target(tool, args) == expected


# -- fail closed -----------------------------------------------------------
def test_a_call_with_no_recorded_decision_is_refused(root: Path) -> None:
    """The wrapper only runs what `aafter_model` classified.

    An unrecorded call can only come from a path that bypassed the model node, so it
    is refused rather than re-decided into an allow.
    """
    middleware = PermissionMiddleware(RulesEngine.load(root, "ask"), run_id="run-1")
    request = ToolCallRequest(
        tool_call={
            "name": "write_file",
            "args": {"file_path": "a.txt", "content": "hello"},
            "id": "c9",
            "type": "tool_call",
        },
        tool=None,
        state={"messages": []},
        runtime=cast(Any, None),
    )
    ran = False

    async def handler(inner: ToolCallRequest) -> ToolMessage:
        nonlocal ran
        ran = True
        return ToolMessage(content="wrote", tool_call_id="c9")

    result = asyncio.run(middleware.awrap_tool_call(request, handler))

    assert ran is False
    assert isinstance(result, ToolMessage)
    assert "Permission denied" in str(result.content)


# -- run manager state machine --------------------------------------------
def test_resolve_records_the_answer_and_refuses_a_second_one(root: Path) -> None:
    async def scenario() -> None:
        manager = RunManager()
        bus = EventBus(storage_path(root, "runs/r1/events.jsonl"), "r1", Redactor([]))
        task = asyncio.create_task(asyncio.sleep(3600))
        run = Run(bus=bus, task=task)
        manager.runs["r1"] = run
        run.pending = ApprovalRequest(
            approval_id="c1",
            run_id="r1",
            kind="tool",
            tool="write_file",
            path="a.txt",
        )
        try:
            with pytest.raises(UnknownApproval):
                await manager.resolve("r1", "other", ApprovalDecision(decision="approve"))

            await manager.resolve("r1", "c1", ApprovalDecision(decision="approve"))
            assert run.answer is not None
            assert run.answer.decision == "approve"
            assert run.ready.is_set()
            assert bus.history[-1].type == "approval.resolved"

            with pytest.raises(UnknownApproval):
                await manager.resolve("r1", "c1", ApprovalDecision(decision="reject"))
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())


class FakeService:
    """Just enough of RunService to exercise the route's status codes."""

    def __init__(self) -> None:
        self.resolved: list[tuple[str, str, str]] = []

    async def start(self, request: RunRequest) -> str:
        return "r1"

    async def stop(self, run_id: str) -> None:
        return None

    async def resolve(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> None:
        if approval_id != "known":
            raise UnknownApproval(approval_id)
        self.resolved.append((run_id, approval_id, decision.decision))

    def events(self, run_id: str, after: int) -> AsyncIterator[Event]:
        raise AssertionError("the route under test never reads the stream")

    def contains(self, run_id: str) -> bool:
        return run_id == "r1"

    async def close(self) -> None:
        return None


def test_interrupt_route_reports_unknown_and_resolved_ids() -> None:
    service = FakeService()
    headers = {"Authorization": "Bearer token"}
    with TestClient(create_app("token", cast(Any, service))) as client:
        ok = client.post(
            "/runs/r1/interrupts/known",
            headers=headers,
            json={"decision": "approve"},
        )
        assert ok.status_code == 200
        assert service.resolved == [("r1", "known", "approve")]

        duplicate = client.post(
            "/runs/r1/interrupts/other",
            headers=headers,
            json={"decision": "reject"},
        )
        assert duplicate.status_code == 409

        unknown_run = client.post(
            "/runs/nope/interrupts/known",
            headers=headers,
            json={"decision": "approve"},
        )
        assert unknown_run.status_code == 404

        invalid = client.post(
            "/runs/r1/interrupts/known",
            headers=headers,
            json={"decision": "maybe"},
        )
        assert invalid.status_code == 422
