"""Real graph/SQLite recovery with partial decisions and an atomic approval ledger."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from test_permissions import FINAL, ScriptedModel

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision, UnknownApproval
from store.catalog import Catalog


async def wait_for(predicate: Any) -> None:
    async with asyncio.timeout(15):
        while not predicate():
            await asyncio.sleep(0.01)


def test_pending_batch_partial_answer_restart_and_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "write_file", "args": {"file_path": name, "content": name}, "id": key}
                    for name, key in (("a.txt", "one"), ("b.txt", "two"))
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        catalog_path = tmp_path / "catalog.json"
        workspace = tmp_path / "project"
        workspace.mkdir()
        manager = RunManager(catalog=Catalog(catalog_path))
        run_id = await manager.start(RunRequest(task="write", workspace=str(workspace)))
        await wait_for(lambda: len(manager.approvals("pending")) == 2)
        await manager.resolve(run_id, "two", ApprovalDecision(decision="reject", reason="keep b"))
        assert not (workspace / "a.txt").exists()
        assert not (workspace / "b.txt").exists()
        await manager.close()
        restarted = RunManager(catalog=Catalog(catalog_path))
        await restarted.recover()
        await wait_for(lambda: restarted.runs[run_id].barrier)
        assert len(restarted.approvals("pending")) == 1
        assert len(restarted.approvals("rejected")) == 1
        with pytest.raises(UnknownApproval):
            await restarted.resolve(run_id, "two", ApprovalDecision(decision="approve"))
        await restarted.resolve(run_id, "one", ApprovalDecision(decision="approve"))
        await wait_for(lambda: restarted.runs[run_id].bus.finished)
        assert (workspace / "a.txt").read_text() == "a.txt"
        assert not (workspace / "b.txt").exists()
        history = restarted.runs[run_id].bus.history
        assert [event.seq for event in history] == list(range(1, len(history) + 1))
        assert sum(event.type == "run.started" for event in history) == 1
        assert sum(event.type == "approval.requested" for event in history) == 2
        assert sum(event.type == "tool.result" for event in history) == 2
        await restarted.close()

    asyncio.run(scenario())
