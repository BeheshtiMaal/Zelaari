"""Real graph/SQLite recovery with partial decisions and an atomic approval ledger."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from pydantic import JsonValue
from test_permissions import FINAL, ScriptedModel

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.rules import RulesEngine
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
        assert sum(
            event.type == "tool.result" and event.call_id in {"one", "two"} for event in history
        ) == 2
        await restarted.close()

    asyncio.run(scenario())


def test_edit_preview_revalidates_and_stages_allow_rule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "src").mkdir()
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_file",
                        "args": {"file_path": "src/a.txt", "content": "original"},
                        "id": "one",
                    }
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager()
        run_id = await manager.start(RunRequest(task="write", workspace=str(tmp_path)))
        await wait_for(lambda: manager.approvals("pending"))
        with pytest.raises(ValueError):
            manager.preview(
                run_id,
                "one",
                ApprovalDecision(
                    decision="approve",
                    edited_args={
                        "file_path": "../escape.txt",
                        "content": "bad",
                    },
                ),
            )
        edited: dict[str, JsonValue] = {"file_path": "src/a.txt", "content": "edited"}
        preview = manager.preview(
            run_id, "one", ApprovalDecision(decision="approve", edited_args=edited)
        )
        assert "+edited" in preview.diff
        await manager.resolve(
            run_id,
            "one",
            ApprovalDecision(
                decision="approve",
                edited_args=edited,
                revision=preview.revision,
                allow_glob="src/**",
            ),
        )
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        assert (tmp_path / "src/a.txt").read_text() == "edited"
        assert RulesEngine.load(tmp_path).rules.tools == {}
        linked = next(
            record
            for record in manager.approvals("pending")
            if record.request.tool == "rules_update"
        )
        await manager.resolve(
            linked.request.run_id, linked.request.approval_id, ApprovalDecision(decision="approve")
        )
        assert RulesEngine.load(tmp_path).rules.tools["write_file"][0].glob == "src/**"
        await manager.close()

    asyncio.run(scenario())


def test_fresh_command_retry_can_be_edited_rejected_or_approved(
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
                        "args": {"command": "Add-Content launches.txt original"},
                        "id": "command-one",
                    }
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager()
        run_id = await manager.start(RunRequest(task="command", workspace=str(tmp_path)))
        await wait_for(lambda: manager.approvals("pending"))
        await manager.resolve(run_id, "command-one", ApprovalDecision(decision="approve"))
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        proposal = manager.retry_command(run_id, "command-one", 300)
        assert proposal.request.args["timeout"] == 300
        await manager.resolve(
            proposal.request.run_id,
            proposal.request.approval_id,
            ApprovalDecision(decision="reject"),
        )
        assert (tmp_path / "launches.txt").read_text().splitlines() == ["original"]
        proposal = manager.retry_command(run_id, "command-one", 300)
        preview = manager.preview(
            proposal.request.run_id,
            proposal.request.approval_id,
            ApprovalDecision(
                decision="approve",
                edited_args={
                    "command": "Add-Content launches.txt edited",
                    "timeout": 300,
                    "mode": "ask",
                },
            ),
        )
        await manager.resolve(
            preview.run_id,
            preview.approval_id,
            ApprovalDecision(decision="approve", revision=preview.revision),
        )
        assert (tmp_path / "launches.txt").read_text().splitlines() == ["original", "edited"]
        await manager.close()

    asyncio.run(scenario())
