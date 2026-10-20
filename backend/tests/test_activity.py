"""Real parent/child streams preserve scope, ordering and truthful telemetry."""

import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from test_readonly_delegates import DelegateProbe

from agent.bridge import RunManager
from agent.events import RunRequest
from agent.meter import TokenMeter
from agent.projection import ActivityProjection
from planning.types import ActivityScope
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor


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
