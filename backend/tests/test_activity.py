"""Real parent/child streams preserve scope, ordering and truthful telemetry."""

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from test_readonly_delegates import DelegateProbe

from agent.bridge import RunManager
from agent.events import RunRequest
from agent.factory import build_agent
from agent.meter import TokenMeter
from agent.projection import ActivityProjection
from permissions.middleware import PermissionMiddleware
from permissions.rules import RulesEngine
from planning.types import ActivityScope
from providers.demo import DemoModel
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor
from tools.fs import WorkspaceBackend


def test_real_delegate_scopes_results_and_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: DelegateProbe(delay=0))
    (tmp_path / "context.txt").write_text("Actual local context", encoding="utf-8")

    async def scenario() -> None:
        catalog = Catalog(tmp_path / "catalog.json", Redactor([DelegateProbe().canary]))
        manager = RunManager(catalog=catalog)
        run_id = await manager.start(
            RunRequest(task="Delegate", workspace=str(tmp_path), mode="auto")
        )
        await asyncio.wait_for(manager.runs[run_id].task, 30)
        events = manager.runs[run_id].bus.history
        assert events[-1].type == "run.finished" and events[-1].status == "completed"
        children = [e for e in events if e.type == "subagent.started"]
        assert {e.scope.agent for e in children} == {"reviewer", "researcher"}
        for child in children:
            end = next(
                e
                for e in events
                if e.type == "subagent.finished" and e.scope.scope_id == child.scope.scope_id
            )
            assert child.seq < end.seq < events[-1].seq
            assert end.result and "Actual local context" in end.result
            turns = [
                e
                for e in events
                if e.type == "activity.started" and e.scope.parent_scope_id == child.scope.scope_id
            ]
            assert turns
            for turn in turns:
                scoped = [e for e in events if getattr(e, "scope", None) == turn.scope]
                assert scoped[0].type == "activity.started"
                assert scoped[-1].type == "activity.finished"
                assert turn.scope.agent == child.scope.agent
        assert [e.seq for e in events] == list(range(1, len(events) + 1))
        assert list(manager.runs[run_id].bus.history) == [
            e async for e in manager.events(run_id, 0)
        ]
        await manager.close()

    asyncio.run(scenario())


def test_context_is_latest_request_and_prose_is_not_summary(tmp_path: Path) -> None:
    async def scenario() -> None:
        bus = EventBus(tmp_path / "events.jsonl", "run", Redactor())
        projection = ActivityProjection(bus, TokenMeter(1), 32000)
        for index in range(2):
            scope = ActivityScope(scope_id=f"turn{index}", turn_id=f"turn{index}", model="fixture")
            await projection.update((), {"before": {"activity_scope": scope.model_dump()}})
            await projection.update(
                (),
                {
                    "model": {
                        "messages": [
                            AIMessage(
                                id=f"m{index}",
                                content="I summarized the conversation",
                                usage_metadata={
                                    "input_tokens": 20,
                                    "output_tokens": 5,
                                    "total_tokens": 25,
                                },
                            )
                        ]
                    }
                },
            )
        context = [e for e in bus.history if e.type == "context.updated"]
        usage = [e for e in bus.history if e.type == "usage.updated"]
        assert context[-1].input_tokens == 20
        assert usage[-1].input_tokens == 40
        assert not any(e.type in {"context.summarized", "reasoning.delta"} for e in bus.history)

    asyncio.run(scenario())


class CompleteWithChild(DemoModel):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(m, SystemMessage) and "read-only" in str(m.content) for m in messages):
            return AIMessage(content="Read-only review done")
        results = [m for m in messages if isinstance(m, ToolMessage)]
        if not results:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "submit_plan",
                        "id": "plan",
                        "args": {"steps": [{"id": "s", "title": "Review"}]},
                    }
                ],
            )
        if len(results) == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_todos",
                        "id": "start",
                        "args": {"todos": [{"content": "[s] Review", "status": "in_progress"}]},
                    }
                ],
            )
        if len(results) == 2:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "task",
                        "id": "child",
                        "args": {"subagent_type": "reviewer", "description": "Review"},
                    },
                    {
                        "name": "write_todos",
                        "id": "finish",
                        "args": {"todos": [{"content": "[s] Review", "status": "completed"}]},
                    },
                ],
            )
        return AIMessage(content="Outcome observed")


def test_parent_cannot_complete_in_the_turn_that_starts_a_delegate(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "graph.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                CompleteWithChild(delay=0),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run"),
            )
            config: RunnableConfig = {"configurable": {"thread_id": "run"}}
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Review"}]}, config
            )
            state = await graph.aget_state(config)
            assert state.values["plan_record"]["progress"][0]["status"] == "in_progress"
            assert any(
                isinstance(m, ToolMessage)
                and m.tool_call_id == "finish"
                and "Wait for delegated work" in str(m.content)
                for m in result["messages"]
            )

    asyncio.run(scenario())


class SlowReasoning(DemoModel):
    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": "Actual reasoning from an active scripted provider",
                },
            )
        )
        await asyncio.Event().wait()


class SummarizingDelegate(DelegateProbe):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        systems = [m for m in messages if isinstance(m, SystemMessage)]
        if not systems:
            return AIMessage(content="Earlier local reads and a denied action.")
        child = any("You are the read-only" in str(m.content) for m in systems)
        if child and any(
            isinstance(m, ToolMessage) and m.tool_call_id == "forbidden" for m in messages
        ):
            return AIMessage(content="Child report after actual compaction")
        return super().answer(messages)


def test_actual_child_summary_notices_and_internal_usage_are_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: SummarizingDelegate(delay=0))
    monkeypatch.setattr(
        "agent.summarization.compute_summarization_defaults",
        lambda model: {
            "trigger": ("messages", 4),
            "keep": ("messages", 2),
        },
    )
    (tmp_path / "context.txt").write_text("Actual local context", encoding="utf-8")

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(
            RunRequest(task="Analyze", workspace=str(tmp_path), mode="auto")
        )
        await asyncio.wait_for(manager.runs[run_id].task, 30)
        events = manager.runs[run_id].bus.history
        assert events[-1].type == "run.finished" and events[-1].status == "completed"
        notices = [e for e in events if e.type == "context.summarized"]
        assert {e.scope.agent for e in notices} >= {"reviewer", "researcher"}
        assert len({e.operation_id for e in notices}) == len(notices)
        assert all(e.affected_messages and e.affected_messages > 0 for e in notices)
        assert any(e.type == "usage.updated" and e.estimated for e in events)
        await manager.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["delegates", "reasoning"])
def test_stop_during_parallel_children_or_reasoning_is_terminal_under_one_second(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    model = DelegateProbe(delay=0) if kind == "delegates" else SlowReasoning(delay=0)
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        entered = 0
        ready = asyncio.Event()

        async def read(*args: Any, **kwargs: Any) -> Any:
            nonlocal entered
            entered += 1
            if entered == 2:
                ready.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(WorkspaceBackend, "aread", read)
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(
            RunRequest(task="Analyze", workspace=str(tmp_path), mode="auto")
        )
        if kind == "delegates":
            await asyncio.wait_for(ready.wait(), 30)
        else:
            async with asyncio.timeout(30):
                while not any(
                    e.type == "reasoning.delta" for e in manager.runs[run_id].bus.history
                ):
                    await asyncio.sleep(0.01)
        started = time.monotonic()
        await manager.stop(run_id)
        assert time.monotonic() - started < 1
        await manager.close()
        events = manager.runs[run_id].bus.history
        assert events[-1].type == "run.finished" and events[-1].status == "stopped"
        assert sum(e.type == "run.finished" for e in events) == 1
        if kind == "delegates":
            assert (
                sum(e.type == "subagent.finished" and e.status == "cancelled" for e in events) == 2
            )

    asyncio.run(scenario())
