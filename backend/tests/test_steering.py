"""Real SQLite delivery, mixed-barrier preservation and steering API boundaries."""

import asyncio
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.activity import identity
from agent.bridge import RunManager
from agent.events import RunRequest
from agent.factory import build_agent
from planning.types import SteeringSubmission
from providers.demo import DemoModel
from providers.question_demo import sample_question
from questions.types import QuestionDecision
from server.app import create_app
from store.catalog import Catalog
from store.secrets import Redactor


class SteeredModel(DemoModel):
    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(
                content="Seen: "
                + " | ".join(str(m.content) for m in messages if isinstance(m, HumanMessage))
            )
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "ask_user_question",
                    "id": "question",
                    "args": {"questions": [sample_question()]},
                }
            ],
        )


async def waiting(manager: RunManager, run_id: str) -> None:
    async with asyncio.timeout(30):
        while not manager.questions(run_id):
            await asyncio.sleep(0.01)


def test_queued_steering_survives_restart_without_releasing_question(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: SteeredModel(delay=0))

    async def scenario() -> None:
        secret = "steering-canary-never-persist"
        catalog = Catalog(tmp_path / "catalog.json", Redactor([secret]))
        manager = RunManager(catalog=catalog)
        run_id = await manager.start(RunRequest(task="Ask first", workspace=str(tmp_path)))
        await waiting(manager, run_id)
        first = SteeringSubmission(submission_id="first", text="Use local files " + secret)
        second = SteeringSubmission(submission_id="second", text="Keep the public API")
        assert (await manager.steer(run_id, first)).status == "queued"
        assert (await manager.steer(run_id, first)).ordinal == 1
        await manager.steer(run_id, second)
        with pytest.raises(ValueError):
            await manager.steer(run_id, first.model_copy(update={"text": "conflict"}))
        assert manager.questions(run_id)[0].status == "pending"
        assert not any(e.type == "tool.result" for e in manager.runs[run_id].bus.history)
        await manager.close()
        restored = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor([secret])))
        await restored.recover()
        await waiting(restored, run_id)
        question = restored.questions(run_id)[0]
        await restored.answer_question(
            run_id,
            "question",
            QuestionDecision(
                interrupt_id=question.interrupt_id,
                status="declined",
            ),
        )
        await asyncio.wait_for(restored.runs[run_id].task, 30)
        run = restored.runs[run_id]
        assert run.steering and [r.status for r in run.steering.records] == ["delivered"] * 2
        assert run.bus.history[-1].type == "run.finished"
        assert run.bus.history[-1].status == "completed"
        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / ".harness/checkpoints.sqlite")
        ) as saver:
            graph = build_agent(tmp_path, SteeredModel(delay=0), saver, Redactor([secret]))
            state = await graph.aget_state({"configurable": {"thread_id": run_id}})
            messages = state.values["messages"]
            for submission in (first, second):
                assert (
                    sum(m.id == identity(run_id + submission.submission_id) for m in messages) == 1
                )
        assert (await restored.steer(run_id, second)).status == "delivered"
        with pytest.raises(ValueError):
            await restored.steer(run_id, SteeringSubmission(submission_id="late", text="Too late"))
        await restored.close()
        for artifact in tmp_path.rglob("*"):
            if artifact.is_file():
                assert secret.encode() not in artifact.read_bytes()

    asyncio.run(scenario())


def test_stop_cancels_pending_messages_and_does_not_release_barrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: SteeredModel(delay=0))

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(RunRequest(task="Ask", workspace=str(tmp_path)))
        await waiting(manager, run_id)
        await manager.steer(run_id, SteeringSubmission(submission_id="pending", text="Wait"))
        started = time.monotonic()
        await manager.stop(run_id)
        assert time.monotonic() - started < 1
        await manager.close()
        queue = manager.runs[run_id].steering
        assert queue and queue.records[0].status == "cancelled"
        assert not any(e.type == "tool.result" for e in manager.runs[run_id].bus.history)

    asyncio.run(scenario())


def test_steering_auth_bounds_and_unknown_run(tmp_path: Path) -> None:
    with TestClient(create_app("test-auth", catalog=Catalog(tmp_path / "catalog.json"))) as client:
        path = "/runs/unknown/messages"
        value = {"submission_id": "id", "text": "next"}
        assert client.post(path, json=value).status_code == 401
        headers = {"Authorization": "Bearer test-auth"}
        assert client.post(path, json=value, headers=headers).status_code == 404
        configuration = client.put(
            "/planning/settings",
            params={"workspace": str(tmp_path)},
            json={"step_threshold": 5},
            headers=headers,
        ).json()["request"]
        assert (
            client.post(
                f"/runs/{configuration['run_id']}/messages", json=value, headers=headers
            ).status_code
            == 409
        )
        for text in (" ", "x" * 32001):
            assert (
                client.post(path, json={**value, "text": text}, headers=headers).status_code == 422
            )
