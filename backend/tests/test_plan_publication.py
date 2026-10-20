"""Durable plan publication survives restart between checkpoint and announcement."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_planning_progress import plan

from planning.publication import publish_plan
from store.eventlog import EventBus
from store.secrets import Redactor


def test_progress_reconciles_once_after_event_log_reconstruction(tmp_path: Path) -> None:
    async def scenario() -> None:
        current = plan(tmp_path)
        path = tmp_path / "events.jsonl"
        bus = EventBus(path, "run", Redactor())
        await publish_plan(bus, current)
        await publish_plan(bus, current)
        current.progress[0].status = "in_progress"
        current.progress[0].started_at = datetime.now(UTC)
        # Simulate checkpoint persisted but publication interrupted by process exit.
        bus = EventBus(path, "run", Redactor())
        await publish_plan(bus, current)
        bus = EventBus(path, "run", Redactor())
        await publish_plan(bus, current)
        assert [event.type for event in bus.history] == ["plan.created", "plan.step.updated"]
        event = bus.history[-1]
        assert event.type == "plan.step.updated"
        assert event.progress == current.progress[0]
        assert [event.seq for event in bus.history] == [1, 2]
        revised = current.model_copy(update={"revision": "f" * 64, "adoption": "approved"})
        await publish_plan(bus, revised)
        await publish_plan(bus, revised)
        assert len(bus.history) == 3
        assert bus.history[-1].type == "plan.created"

    asyncio.run(scenario())


def test_unaccepted_or_foreign_plan_cannot_publish(tmp_path: Path) -> None:
    async def scenario() -> None:
        bus = EventBus(tmp_path / "events.jsonl", "run", Redactor())
        current = plan(tmp_path)
        await publish_plan(bus, None)
        for adoption in ("pending", "rejected"):
            await publish_plan(bus, current.model_copy(update={"adoption": adoption}))
        assert not bus.history
        with pytest.raises(ValueError, match="another run"):
            await publish_plan(bus, current.model_copy(update={"run_id": "foreign"}))
        assert not bus.history

    asyncio.run(scenario())
