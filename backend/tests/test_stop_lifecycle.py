"""Stop terminates real owned processes and commits terminal events in one flush."""

import asyncio
import os
import threading
import time
from pathlib import Path

import psutil
import pytest
from langchain_core.messages import AIMessage
from test_permissions import FINAL, ScriptedModel

from agent.bridge import RunManager
from agent.events import RunRequest
from planning.types import ActivityScope
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor
from tools.fs import WorkspaceBackend


def test_terminal_batch_has_one_flush_and_rejects_late_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        bus = EventBus(tmp_path / "events.jsonl", "run", Redactor())
        await bus.emit("activity.started", scope=ActivityScope(scope_id="scope"))
        flushes = 0
        original = os.fsync

        def flush(fd: int) -> None:
            nonlocal flushes
            flushes += 1
            original(fd)

        monkeypatch.setattr("store.eventlog.os.fsync", flush)
        await bus.emit_many(
            [
                (
                    "activity.finished",
                    {"scope": ActivityScope(scope_id="scope"), "status": "cancelled"},
                ),
                ("run.finished", {"status": "stopped"}),
            ]
        )
        await bus.emit("message.delta", message_id="late", text="must not publish")
        assert flushes == 1
        assert EventBus(bus.path, "run", Redactor()).history == bus.history
        assert len(bus.history) == 3

    asyncio.run(scenario())


def test_cancelled_file_replacement_does_not_publish_a_late_mutation(tmp_path: Path) -> None:
    target = tmp_path / "original.txt"
    target.write_text("before", encoding="utf-8")
    cancelled = threading.Event()
    cancelled.set()
    backend = WorkspaceBackend(tmp_path, Redactor(), cancelled=cancelled)
    assert backend.edit("original.txt", "before", "after").error
    assert backend.write("new.txt", "late").error
    assert backend.delete("original.txt").error
    assert target.read_text(encoding="utf-8") == "before"
    assert not (tmp_path / "new.txt").exists()
    assert not list(tmp_path.glob(".harness-tmp-*"))


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="Windows owned process lifetime")
def test_stop_acknowledges_under_one_second_and_kills_owned_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "run_command",
                        "id": "command",
                        "args": {
                            "command": (
                                "$PID | Set-Content parent.pid; Start-Sleep 60; Write-Output late"
                            ),
                        },
                    }
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(
            RunRequest(task="Run command", workspace=str(tmp_path), mode="auto")
        )
        async with asyncio.timeout(30):
            while not (tmp_path / "parent.pid").exists():
                await asyncio.sleep(0.02)
        process = int((tmp_path / "parent.pid").read_text(encoding="utf-8").strip())
        assert psutil.pid_exists(process)
        started = time.monotonic()
        await manager.stop(run_id)
        assert time.monotonic() - started < 1
        async with asyncio.timeout(10):
            while psutil.pid_exists(process):
                await asyncio.sleep(0.02)
        await manager.close()
        events = manager.runs[run_id].bus.history
        assert events[-1].type == "run.finished" and events[-1].status == "stopped"
        assert not any(e.type == "tool.result" and e.call_id == "command" for e in events)

    asyncio.run(scenario())
