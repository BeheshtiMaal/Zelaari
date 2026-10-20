"""Actual termination, redaction, cancellation and malformed request boundaries."""

import asyncio
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from pydantic import SecretStr
from test_approval_recovery import wait_for
from test_permissions import FINAL, ScriptedModel
from test_questions import question

from agent.bridge import RunManager
from agent.events import RunRequest
from providers.base import ModelInput, Probe
from questions.types import QuestionDecision, QuestionSelection
from store.catalog import Catalog, Credential
from store.secrets import Redactor


def test_killed_question_engine_resumes_original_mixed_barrier(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    worker = Path(__file__).with_name("question_worker.py")
    env = {**os.environ, "PYTHONPATH": str(worker.parents[1])}
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [sys.executable, str(worker), str(root), "start"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )
    try:
        output = process.stdout
        assert output is not None
        ready: queue.Queue[bytes] = queue.Queue()
        threading.Thread(target=lambda: ready.put(output.readline()), daemon=True).start()
        run_id = json.loads(ready.get(timeout=45))["run_id"]
        assert not (root / "demo-answer.txt").exists()
        process.kill()
        process.communicate(timeout=10)
        result = subprocess.run(
            [sys.executable, str(worker), str(root), "resume"],
            env=env,
            capture_output=True,
            creationflags=flags,
            timeout=45,
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        assert (root / "demo-answer.txt").read_text() == "Approved mixed effect\n"
        events = [
            json.loads(line)
            for line in (root / f".harness/runs/{run_id}/events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert sum(event["type"] == "question.asked" for event in events) == 1
        assert sum(event["type"] == "question.answered" for event in events) == 1
        assert (
            sum(
                event["type"] == "steering.updated" and event["message"]["status"] == "delivered"
                for event in events
            )
            == 1
        )
        assert (
            sum(
                event["type"] == "tool.result" and event["call_id"] == "demo-mixed-write"
                for event in events
            )
            == 1
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


@pytest.mark.parametrize("stop", [False, True])
def test_question_privacy_and_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop: bool
) -> None:
    secret = "synthetic-question-secret-canary"
    payload = question()
    payload["text"] = "Preference " + secret
    payload["options"][0]["description"] = "Description " + secret
    payload["options"][0]["label"] = "Option " + secret
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ask_user_question",
                        "id": "ask",
                        "args": {"questions": [payload], "context": "Context " + secret},
                    },
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json", Redactor([secret])))
        run_id = await manager.start(RunRequest(task="ask", workspace=str(tmp_path)))
        await wait_for(lambda: manager.questions(run_id))
        record = manager.questions(run_id)[0]
        assert secret not in record.model_dump_json()
        answer = QuestionDecision(
            interrupt_id=record.interrupt_id,
            status="answered",
            answers=[QuestionSelection(question_id="q", other="Preference " + secret)],
        )
        if stop:
            await manager.stop(run_id)
            with pytest.raises(ValueError):
                await manager.answer_question(run_id, "ask", answer)
        else:
            await manager.answer_question(run_id, "ask", answer)
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        await manager.close()
        for path in tmp_path.rglob("*"):
            if path.is_file():
                assert secret.encode() not in path.read_bytes(), path.name

    asyncio.run(scenario())


def test_question_recovery_preserves_missing_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "synthetic-question-vault-canary"
    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "ask_user_question", "id": "ask", "args": {"questions": [question()]}},
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.chat_model", lambda *args: model)

    async def scenario() -> None:
        root = tmp_path / "project"
        root.mkdir()
        path = tmp_path / "catalog.json"
        catalog = Catalog(path)
        catalog.credential(Credential(id="fixture", key=SecretStr(secret)))
        provider = catalog.save(
            ModelInput(
                id="fixture", name="Fixture", base_url="https://fixture.invalid/v1", model="fixture"
            )
        )
        provider.supports_tools = True
        provider.probe = Probe(status="ok")
        catalog.persist()
        manager = RunManager(catalog=catalog)
        run_id = await manager.start(RunRequest(task="ask", workspace=str(root), model="fixture"))
        await wait_for(lambda: manager.questions(run_id))
        original = manager.questions(run_id)[0]
        await manager.close()
        restored = RunManager(catalog=Catalog(path))
        await restored.recover()
        assert not restored.runs
        assert restored.questions(run_id)[0].status == "pending"
        restored.catalog.credential(Credential(id="fixture", key=SecretStr(secret)))
        current = restored.catalog.data.models["fixture"]
        old_url = current.base_url
        current.base_url = "https://changed.invalid/v1"
        await restored.recover()
        assert not restored.runs
        current.base_url = old_url
        moved = tmp_path / "temporarily-unavailable"
        root.rename(moved)
        await restored.recover()
        assert not restored.runs
        moved.rename(root)
        await restored.recover()
        await restored.answer_question(
            run_id, "ask", QuestionDecision(interrupt_id=original.interrupt_id, status="declined")
        )
        await wait_for(lambda: restored.runs[run_id].bus.finished)
        assert restored.questions(run_id)[0].status == "declined"
        await restored.close()
        for target in tmp_path.rglob("*"):
            if target.is_file():
                assert secret.encode() not in target.read_bytes()

    asyncio.run(scenario())
