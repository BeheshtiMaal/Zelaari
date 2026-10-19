"""Real agent questions, independent mixed decisions and original-run restoration."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from test_approval_recovery import wait_for
from test_permissions import FINAL, ScriptedModel
from test_questions import question

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision
from questions.types import QuestionDecision, QuestionSelection
from server.app import create_app
from store.catalog import Catalog


@pytest.mark.parametrize("question_first", [True, False])
def test_mixed_question_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, question_first: bool
) -> None:
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "ask_user_question", "args": {"questions": [question()]}, "id": "ask"},
                    {
                        "name": "write_file",
                        "args": {"file_path": "a.txt", "content": "once"},
                        "id": "write",
                    },
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        root = tmp_path / "project"
        root.mkdir()
        path = tmp_path / "catalog.json"
        manager = RunManager(catalog=Catalog(path))
        run_id = await manager.start(RunRequest(task="mixed", workspace=str(root)))
        await wait_for(lambda: manager.questions(run_id))
        record = manager.questions(run_id)[0]
        answer = QuestionDecision(interrupt_id=record.interrupt_id, status="declined")
        if question_first:
            await manager.answer_question(run_id, "ask", answer)
        else:
            await manager.resolve(run_id, "write", ApprovalDecision(decision="approve"))
        assert not (root / "a.txt").exists()
        assert manager.catalog.data.workspaces.tasks[0].waiting_on == [
            "approval" if question_first else "question"
        ]
        await manager.close()
        restarted = RunManager(catalog=Catalog(path))
        await restarted.recover()
        if question_first:
            await restarted.resolve(run_id, "write", ApprovalDecision(decision="approve"))
        else:
            await restarted.answer_question(run_id, "ask", answer)
        await wait_for(lambda: restarted.runs[run_id].bus.finished)
        history = restarted.runs[run_id].bus.history
        assert (root / "a.txt").read_text() == "once"
        assert sum(event.type == "question.asked" for event in history) == 1
        assert sum(event.type == "question.answered" for event in history) == 1
        results = [
            json.loads(event.text)
            for event in history
            if event.type == "tool.result" and event.call_id == "ask"
        ]
        assert results[0]["status"] == "declined"
        assert restarted.catalog.data.workspaces.tasks[0].waiting_on == []
        with pytest.raises(ValueError):
            await restarted.answer_question(run_id, "ask", answer)
        await restarted.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["ask", "auto", "read-only"])
def test_question_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    from typing import cast

    from permissions.types import Mode

    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ask_user_question",
                        "args": {"questions": [question("rank")]},
                        "id": "ask",
                    },
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)
    catalog = Catalog(tmp_path / "catalog.json")
    app = create_app("test-token", catalog=catalog)
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(app, headers=headers) as client:
        run_id = client.post(
            "/runs", json={"task": "ask", "workspace": str(tmp_path), "mode": cast(Mode, mode)}
        ).json()["run_id"]
        import time

        for _ in range(200):
            records = client.get(f"/runs/{run_id}/questions").json()
            if records:
                break
            time.sleep(0.02)
        assert len(records) == 1
        assert client.get("/approvals").json() == []
        route = f"/runs/{run_id}/interrupts/ask"
        answer = {
            "kind": "question",
            "interrupt_id": records[0]["interrupt_id"],
            "status": "answered",
            "answers": [{"question_id": "q", "option_ids": ["b", "a"]}],
        }
        assert client.post(route, json=answer, headers={"Authorization": "bad"}).status_code == 401
        assert client.post(route, json={**answer, "interrupt_id": "wrong"}).status_code == 409
        assert client.post(route, json={**answer, "answers": []}).status_code == 409
        assert client.post(route, json=answer).status_code == 200
        assert client.post(route, json=answer).status_code == 409
        configuration = client.put(
            "/rules", params={"workspace": str(tmp_path)}, json={"mode": "ask", "tools": {}}
        ).json()
        config_request = configuration["request"]
        assert (
            client.post(
                f"/runs/{config_request['run_id']}/interrupts/{config_request['approval_id']}",
                json=answer,
            ).status_code
            == 409
        )
        assert not (tmp_path / ".harness/rules.json").exists()


def test_two_question_calls_hold_all_sibling_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "ask_user_question", "args": {"questions": [question()]}, "id": "one"},
                    {
                        "name": "ask_user_question",
                        "args": {"questions": [question("rank")]},
                        "id": "two",
                    },
                    {
                        "name": "write_file",
                        "args": {"file_path": "effect.txt", "content": "once"},
                        "id": "effect",
                    },
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(
            RunRequest(task="questions", workspace=str(tmp_path), mode="auto")
        )
        await wait_for(lambda: len(manager.questions(run_id)) == 2)
        records = manager.questions(run_id)
        await manager.answer_question(
            run_id,
            "two",
            QuestionDecision(
                interrupt_id=records[1].interrupt_id,
                status="answered",
                answers=[QuestionSelection(question_id="q", option_ids=["b", "a"])],
            ),
        )
        assert not (tmp_path / "effect.txt").exists()
        await manager.answer_question(
            run_id, "one", QuestionDecision(interrupt_id=records[0].interrupt_id, status="declined")
        )
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        assert (tmp_path / "effect.txt").read_text() == "once"
        results = {
            event.call_id: json.loads(event.text)
            for event in manager.runs[run_id].bus.history
            if event.type == "tool.result" and event.call_id in {"one", "two"}
        }
        assert results["one"]["status"] == "declined"
        assert results["two"]["answers"][0]["option_ids"] == ["b", "a"]
        await manager.close()

    asyncio.run(scenario())
