"""A scheduled run is an ordinary run: the same barrier, the same inbox, its own event log."""

import asyncio
from datetime import datetime
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from agent.bridge import RunManager
from permissions.types import ApprovalDecision
from scheduling.model import ScheduleInput
from scheduling.ticker import Scheduler
from store.catalog import Catalog
from store.schedules import add_schedule, find_schedule
from test_approval_recovery import wait_for
from test_permissions import FINAL, ScriptedModel
from tools.jail import storage_path

NOW = datetime(2026, 10, 21, 12, 0)


def status_of(catalog: Catalog, schedule_id: str) -> str | None:
    found = find_schedule(catalog, schedule_id)
    return found.last_status if found else None


def write_turn(name: str = "a.txt", content: str = "hello") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "write_file", "args": {"file_path": name, "content": content}, "id": "one"}
        ],
    )


def command_turn(command: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "run_command", "args": {"command": command}, "id": "one"}],
    )


def start(
    tmp_path: Path, model: ScriptedModel, monkeypatch: pytest.MonkeyPatch, **overrides: object
) -> tuple[Catalog, RunManager, Scheduler, str, Path]:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)
    catalog = Catalog(tmp_path / "catalog.json")
    manager = RunManager(catalog=catalog)
    fields: dict[str, object] = {
        "name": "Weekly dependency check",
        "prompt": "Look for old or unsafe packages",
        "workspace": str(workspace),
        "model": "demo",
        "mode": "ask",
        "ceiling": "full",
    }
    fields.update(overrides)
    seeded = add_schedule(catalog, ScheduleInput.model_validate(fields), NOW)
    scheduler = Scheduler(
        catalog,
        manager.start,
        clock=lambda: NOW,
        events=lambda run_id: manager.events(run_id, 0),
    )
    return catalog, manager, scheduler, seeded.id, workspace


def test_queued_approval_pauses_and_resumes_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ScriptedModel(replies=[write_turn(), FINAL])
    catalog, manager, scheduler, schedule_id, workspace = start(tmp_path, model, monkeypatch)

    async def scenario() -> None:
        run_id = await scheduler.run_now(schedule_id)
        await wait_for(lambda: manager.approvals("pending"))

        pending = manager.approvals("pending")
        assert len(pending) == 1
        request = pending[0].request
        assert request.run_id == run_id
        # The card says which schedule asked, not what the prompt was.
        assert (request.source_kind, request.source_title) == (
            "schedule",
            "Weekly dependency check",
        )

        # Paused: no terminal event, and the effect has not happened.
        log = storage_path(workspace, f"runs/{run_id}/events.jsonl")
        assert "run.finished" not in log.read_text(encoding="utf-8")
        assert not (workspace / "a.txt").exists()

        # The task under the workspace carries the schedule, which is what the row counts.
        task = next(item for item in catalog.data.workspaces.tasks if item.id == run_id)
        assert task.schedule_id == schedule_id

        await manager.resolve(
            run_id, pending[0].request.approval_id, ApprovalDecision(decision="approve")
        )
        await wait_for(lambda: "run.finished" in log.read_text(encoding="utf-8"))
        assert (workspace / "a.txt").read_text(encoding="utf-8") == "hello"
        # The watcher copies the outcome onto the row.
        await wait_for(lambda: status_of(catalog, schedule_id) == "completed")

        await scheduler.close()
        await manager.close()

    asyncio.run(scenario())


def test_a_rejected_approval_still_ends_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ScriptedModel(replies=[write_turn("b.txt"), FINAL])
    catalog, manager, scheduler, schedule_id, workspace = start(tmp_path, model, monkeypatch)

    async def scenario() -> None:
        run_id = await scheduler.run_now(schedule_id)
        await wait_for(lambda: manager.approvals("pending"))
        pending = manager.approvals("pending")
        await manager.resolve(
            run_id, pending[0].request.approval_id, ApprovalDecision(decision="reject")
        )
        log = storage_path(workspace, f"runs/{run_id}/events.jsonl")
        await wait_for(lambda: "run.finished" in log.read_text(encoding="utf-8"))
        # Rejecting is not a crash: the run ends and nothing was written.
        assert not (workspace / "b.txt").exists()
        assert status_of(catalog, schedule_id) is not None
        await scheduler.close()
        await manager.close()

    asyncio.run(scenario())


def test_full_access_never_bypasses_the_always_ask_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole promise of the ceiling: auto still stops at a destructive command."""
    model = ScriptedModel(replies=[command_turn("rm -rf build"), FINAL])
    catalog, manager, scheduler, schedule_id, workspace = start(
        tmp_path, model, monkeypatch, mode="auto", ceiling="full"
    )

    async def scenario() -> None:
        run_id = await scheduler.run_now(schedule_id)
        await wait_for(lambda: manager.approvals("pending"))
        pending = manager.approvals("pending")
        assert len(pending) == 1
        assert pending[0].request.risk.level == "high"
        # Nothing ran: the barrier is before the effect, not after it.
        assert not (workspace / "build").exists()
        await manager.stop(run_id)
        await scheduler.close()
        await manager.close()

    asyncio.run(scenario())


def test_the_scheduled_run_writes_its_own_event_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ScriptedModel(replies=[write_turn("c.txt"), FINAL])
    catalog, manager, scheduler, schedule_id, workspace = start(tmp_path, model, monkeypatch)

    async def scenario() -> None:
        run_id = await scheduler.run_now(schedule_id)
        await wait_for(lambda: manager.approvals("pending"))
        pending = manager.approvals("pending")
        await manager.resolve(
            run_id, pending[0].request.approval_id, ApprovalDecision(decision="approve")
        )
        log = storage_path(workspace, f"runs/{run_id}/events.jsonl")
        await wait_for(lambda: "run.finished" in log.read_text(encoding="utf-8"))
        assert '"type":"run.started"' in log.read_text(encoding="utf-8")
        # The request artefact names the schedule: the run's own record of why it exists.
        request = storage_path(workspace, f"runs/{run_id}/request.json")
        assert schedule_id in request.read_text(encoding="utf-8")
        await scheduler.close()
        await manager.close()

    asyncio.run(scenario())
