"""Failure boundaries: stopped decisions, unavailable credentials, and torn event appends."""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from pydantic import SecretStr
from test_approval_recovery import wait_for
from test_permissions import FINAL, ScriptedModel

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision, UnknownApproval
from providers.base import ModelInput, Probe
from server.app import create_app
from store.catalog import Catalog, Credential
from store.eventlog import EventBus
from store.secrets import Redactor


def test_event_log_recovers_only_incomplete_last_append(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"

    async def scenario() -> None:
        bus = EventBus(path, "run", Redactor())
        await bus.emit("run.started", task="fixture", model="demo")
        with path.open("ab") as stream:
            stream.write(b'{"run_id":"run","seq":2,"type":"mess')
        restored = EventBus(path, "run", Redactor())
        await restored.emit("message.delta", message_id="message", text="recovered")
        assert [event.seq for event in restored.history] == [1, 2]
        assert len(path.read_text().splitlines()) == 2

    asyncio.run(scenario())
    with path.open("ab") as stream:
        stream.write(b"{}\n")
    with pytest.raises(ValueError):
        EventBus(path, "run", Redactor())


def test_stopped_pending_run_cannot_execute_after_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_file",
                        "args": {"file_path": "a.txt", "content": "unsafe"},
                        "id": "one",
                    }
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(RunRequest(task="write", workspace=str(tmp_path)))
        await wait_for(lambda: manager.approvals("pending"))
        await manager.stop(run_id)
        with pytest.raises(UnknownApproval):
            await manager.resolve(run_id, "one", ApprovalDecision(decision="approve"))
        await manager.close()
        restarted = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        await restarted.recover()
        assert not restarted.runs
        assert not restarted.approvals("pending")
        assert not (tmp_path / "a.txt").exists()

    asyncio.run(scenario())


def test_approval_routes_require_auth() -> None:
    with TestClient(create_app("boundary-token")) as client:
        for method, path in [
            ("GET", "/approvals"),
            ("PUT", "/rules?workspace=missing"),
            ("POST", "/runs/missing/interrupts/missing"),
            ("POST", "/runs/missing/interrupts/missing/preview"),
            ("POST", "/runs/missing/commands/missing/retry"),
        ]:
            assert client.request(method, path, json={}).status_code == 401


def test_missing_credential_preserves_pending_and_redacts_all_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "phase4-sensitive-canary-69731"
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_file",
                        "args": {"file_path": "a.txt", "content": secret},
                        "id": "one",
                    }
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.chat_model", lambda *args: model)

    async def scenario() -> None:
        path = tmp_path / "catalog.json"
        catalog = Catalog(path)
        catalog.credential(Credential(id="fixture", key=SecretStr(secret)))
        record = catalog.save(
            ModelInput(
                id="fixture", name="Fixture", base_url="https://fixture.invalid/v1", model="fixture"
            )
        )
        record.supports_tools = True
        record.probe = Probe(status="ok")
        catalog.persist()
        manager = RunManager(catalog=catalog)
        run_id = await manager.start(
            RunRequest(task="write", workspace=str(tmp_path), model="fixture")
        )
        await wait_for(lambda: manager.approvals("pending"))
        with pytest.raises(ValueError, match="Secret"):
            manager.preview(
                run_id,
                "one",
                ApprovalDecision(
                    decision="approve",
                    edited_args={
                        "file_path": "a.txt",
                        "content": secret,
                    },
                ),
            )
        await manager.close()
        restarted = RunManager(catalog=Catalog(path))
        await restarted.recover()
        assert not restarted.runs
        assert len(restarted.approvals("pending")) == 1
        restarted.catalog.credential(Credential(id="fixture", key=SecretStr(secret)))
        await restarted.recover()
        await wait_for(lambda: restarted.runs[run_id].barrier)
        await restarted.resolve(run_id, "one", ApprovalDecision(decision="reject", reason=secret))
        await wait_for(lambda: restarted.runs[run_id].bus.finished)
        await restarted.close()
        assert not (tmp_path / "a.txt").exists()
        for target in tmp_path.rglob("*"):
            if target.is_file():
                assert secret.encode() not in target.read_bytes(), target.name

    asyncio.run(scenario())
