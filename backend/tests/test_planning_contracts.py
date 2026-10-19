"""Phase 6 bounded schemas and executable installed-runtime contracts."""

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgentMiddleware
from deepagents.middleware.summarization import SummarizationMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, ValidationError

from planning.readonly import ReadOnlyDelegateMiddleware
from planning.types import PlanningSettings, PlanSubmission, SteeringSubmission
from providers.demo import DemoModel
from store.secrets import Redactor
from tools.fs import WorkspaceBackend


@pytest.mark.parametrize(
    "pattern", ["../x", "/tmp/x", "C:/x", "a\\x", "a/../b", "a:secret", " x", ".", "x\x00"]
)
def test_plan_rejects_unsafe_patterns(pattern: str) -> None:
    with pytest.raises(ValidationError):
        PlanSubmission.model_validate(
            {"steps": [{"id": "s", "title": "Read", "expected_files": [pattern]}]}
        )


@pytest.mark.parametrize(
    "value",
    [
        {"steps": []},
        {"steps": [{"id": "s", "title": "  "}]},
        {"steps": [{"id": "s", "title": "A"}] * 2},
        {"steps": [{"id": str(n), "title": "A"} for n in range(65)]},
        {"steps": [{"id": "s", "title": "A", "status": "completed"}]},
    ],
)
def test_plan_bounds_and_engine_owned_progress(value: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PlanSubmission.model_validate(value)


@pytest.mark.parametrize("value", [0, -1, 65, True, 1.5, "4"])
def test_settings_threshold_is_bounded_integer(value: Any) -> None:
    with pytest.raises(ValidationError):
        PlanningSettings.model_validate({"step_threshold": value})


def test_steering_bounds() -> None:
    for text in (" ", "x" * 32001):
        with pytest.raises(ValidationError):
            SteeringSubmission(submission_id="message", text=text)
    assert SteeringSubmission(submission_id="message", text=" next ").text == "next"


def test_installed_todos_have_no_id_or_failed_state() -> None:
    schema = cast(
        type[BaseModel], TodoListMiddleware().tools[0].get_input_schema()
    ).model_json_schema()
    todo = schema["$defs"]["Todo"]
    assert set(todo["properties"]) == {"content", "status"}
    assert todo["properties"]["status"]["enum"] == ["pending", "in_progress", "completed"]


class DelegateModel(DemoModel):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="Parent observed both results")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "task",
                    "args": {"subagent_type": name, "description": name},
                    "id": name,
                    "type": "tool_call",
                }
                for name in ("reviewer", "researcher")
            ],
        )


class ReaderModel(DemoModel):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="Read-only result")
        return AIMessage(
            content="",
            tool_calls=[{"name": "rendezvous", "args": {}, "id": "read", "type": "tool_call"}],
        )


class ForbiddenModel(DemoModel):
    requested_name: str

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="Outcome observed")
        return AIMessage(
            content="",
            tool_calls=[
                {"name": self.requested_name, "args": {}, "id": "forbidden", "type": "tool_call"}
            ],
        )


def test_real_parallel_compiled_children_and_namespaces(tmp_path: Path) -> None:
    async def scenario() -> None:
        entered = 0
        both = asyncio.Event()

        @tool
        async def rendezvous() -> str:
            """Wait until both real child tools have started."""
            nonlocal entered
            entered += 1
            if entered == 2:
                both.set()
            await asyncio.wait_for(both.wait(), timeout=5)
            return "Both children ran concurrently"

        backend = WorkspaceBackend(tmp_path, Redactor())
        children: list[CompiledSubAgent] = [
            {
                "name": name,
                "description": name,
                "runnable": create_agent(ReaderModel(delay=0), tools=[rendezvous]),
            }
            for name in ("reviewer", "researcher")
        ]
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "parallel.sqlite")) as saver:
            graph = create_deep_agent(
                model=DelegateModel(delay=0),
                backend=backend,
                checkpointer=saver,
                middleware=[SubAgentMiddleware(backend=backend, subagents=children)],
            )
            namespaces: set[tuple[str, ...]] = set()
            config: RunnableConfig = {"configurable": {"thread_id": "parallel"}}
            async for namespace, _ in graph.astream(
                {"messages": [HumanMessage(content="Delegate")]},
                config,
                stream_mode="updates",
                subgraphs=True,
                durability="sync",
            ):
                if namespace:
                    namespaces.add(cast(tuple[str, ...], namespace))
            assert entered == 2
            assert len(namespaces) == 2
            snapshot = await graph.aget_state(config)
            assert not snapshot.next
            outputs = [m for m in snapshot.values["messages"] if isinstance(m, ToolMessage)]
            assert {m.tool_call_id for m in outputs} == {"reviewer", "researcher"}
            assert all("Read-only result" in str(m.content) for m in outputs)

    asyncio.run(scenario())


class SummaryModel(DemoModel):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        return AIMessage(content="Actual concise summary or final response")


def test_real_summarizer_persists_transition_not_prose(tmp_path: Path) -> None:
    async def scenario() -> None:
        backend = WorkspaceBackend(tmp_path, Redactor())
        model = SummaryModel(delay=0)
        summary = SummarizationMiddleware(
            model,
            backend=backend,
            trigger=("messages", 4),
            keep=("messages", 2),
        )
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "summary.sqlite")) as saver:
            graph = create_deep_agent(
                model=model,
                backend=backend,
                checkpointer=saver,
                middleware=cast(
                    list[AgentMiddleware[Any, Any, Any]],
                    [summary, FilesystemMiddleware(backend=backend, tools=["read_file"])],
                ),
            )
            config: RunnableConfig = {"configurable": {"thread_id": "summary"}}
            messages: list[BaseMessage] = []
            for index in range(4):
                messages.extend(
                    [HumanMessage(content=f"Question {index}"), AIMessage(content="Answer")]
                )
            await graph.ainvoke(cast(Any, {"messages": messages}), config)
            snapshot = await graph.aget_state(config)
            event = snapshot.values["_summarization_event"]
            assert event["cutoff_index"] > 0
            assert event["summary_message"].additional_kwargs["lc_source"] == "summarization"
            assert "Actual concise summary" in event["summary_message"].content
            # Raw history remains available for audit: compaction changes effective input.
            assert len(snapshot.values["messages"]) >= len(messages)
            assert event["file_path"]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "name", ["write_file", "edit_file", "delete", "run_command", "task", "settings", "unknown"]
)
def test_delegate_ceiling_denies_even_registered_tools(name: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        executed = False

        @tool(name)
        async def forbidden() -> str:
            """Must never execute even when registered."""
            nonlocal executed
            executed = True
            return "Forbidden effect"

        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "ceiling.sqlite")) as saver:
            graph = create_agent(
                ForbiddenModel(requested_name=name, delay=0),
                tools=[forbidden],
                middleware=[ReadOnlyDelegateMiddleware()],
                checkpointer=saver,
            )
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content="Try a forbidden tool")]},
                {"configurable": {"thread_id": "ceiling"}},
            )
            outputs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
            assert not executed
            assert outputs[0].status == "error"
            assert "Permission denied" in str(outputs[0].content)

    asyncio.run(scenario())
