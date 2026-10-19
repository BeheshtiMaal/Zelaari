"""Interview state is structural, durable and never permission to mutate."""

import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from test_approval_recovery import wait_for
from test_permissions import FINAL, ScriptedModel
from test_questions import question

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision
from questions.types import QuestionDecision, QuestionSelection
from store.catalog import Catalog
from store.secrets import Redactor


def test_grill_restart_and_structured_ready(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "catalog.json"
        manager = RunManager(catalog=Catalog(path), demo_delay=0)
        run_id = await manager.start(
            RunRequest(task="/grill improve parser", workspace=str(tmp_path))
        )
        await wait_for(lambda: manager.questions(run_id))

        async def answer(current: RunManager, index: int) -> None:
            record = current.questions(run_id)[index]
            await current.answer_question(
                run_id,
                record.request.call_id,
                QuestionDecision(
                    interrupt_id=record.interrupt_id,
                    status="answered",
                    answers=[
                        QuestionSelection(
                            question_id=record.request.questions[0].id,
                            other="Keep scope small and test it",
                        )
                    ],
                ),
            )

        await answer(manager, 0)
        await wait_for(lambda: len(manager.questions(run_id)) == 2)
        await manager.close()
        restored = RunManager(catalog=Catalog(path), demo_delay=0)
        await restored.recover()
        await answer(restored, 1)
        await wait_for(lambda: restored.runs[run_id].bus.finished)
        history = restored.runs[run_id].bus.history
        assert any(
            event.type == "tool.result" and event.call_id == "ready" and "acceptance" in event.text
            for event in history
        )
        assert all(record.status == "answered" for record in restored.questions(run_id))
        assert sum(event.type == "question.asked" for event in history) == 2
        await restored.close()

    asyncio.run(scenario())


def test_exhausted_choices_return_hints_and_keep_approved_changes(tmp_path: Path) -> None:
    import json

    secret = "synthetic-exhaustion-hint-canary"

    async def scenario() -> None:
        (tmp_path / "README.md").write_text("before", encoding="utf-8")
        manager = RunManager(
            catalog=Catalog(tmp_path / "catalog.json", Redactor([secret])), demo_delay=0
        )
        edit_id = await manager.start(
            RunRequest(task="demo edit README.md: before => after", workspace=str(tmp_path))
        )
        await wait_for(lambda: manager.approvals("pending"))
        await manager.resolve(edit_id, "demo-edit", ApprovalDecision(decision="approve"))
        await wait_for(lambda: manager.runs[edit_id].bus.finished)
        for choice in ("retry", "change", "stop"):
            run_id = await manager.start(
                RunRequest(task="demo question exhausted", workspace=str(tmp_path))
            )
            await wait_for(lambda: manager.questions(run_id))
            record = manager.questions(run_id)[0]
            assert record.request.failure is not None
            assert record.request.failure.attempts == 3
            hint = "Inspect date normalization " + secret if choice == "retry" else None
            await manager.answer_question(
                run_id,
                record.request.call_id,
                QuestionDecision(
                    interrupt_id=record.interrupt_id,
                    status="answered",
                    answers=[
                        QuestionSelection(question_id="exhausted", option_ids=[choice], hint=hint)
                    ],
                ),
            )
            await wait_for(lambda: manager.runs[run_id].bus.finished)
            results = [
                json.loads(event.text)
                for event in manager.runs[run_id].bus.history
                if event.type == "tool.result" and event.call_id == "demo-question"
            ]
            assert results[0]["answers"][0]["option_ids"] == [choice]
            assert results[0]["answers"][0]["hint"] == (
                manager.redactor.text(hint) if hint else None
            )
            assert (tmp_path / "README.md").read_text(encoding="utf-8") == "after"
        await manager.close()
        for target in tmp_path.rglob("*"):
            if target.is_file():
                assert secret.encode() not in target.read_bytes()

    asyncio.run(scenario())


def test_grill_prose_cannot_finish_without_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ScriptedModel(
        replies=[
            FINAL,
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ask_user_question",
                        "args": {"questions": [question()]},
                        "id": "ask",
                    }
                ],
            ),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(RunRequest(task="/grill goal", workspace=str(tmp_path)))
        await wait_for(lambda: manager.questions(run_id))
        assert not manager.runs[run_id].bus.finished
        record = manager.questions(run_id)[0]
        await manager.answer_question(
            run_id, "ask", QuestionDecision(interrupt_id=record.interrupt_id, status="declined")
        )
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        assert not manager.approvals()
        await manager.close()

    asyncio.run(scenario())


def test_grill_denies_premature_and_same_turn_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = {key: "Specified" for key in ("objective", "scope", "constraints", "acceptance")}

    def write(identifier: str) -> dict[str, object]:
        return {
            "name": "write_file",
            "id": identifier,
            "args": {"file_path": identifier, "content": "bad"},
        }

    model = ScriptedModel(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    write("early"),
                    {"name": "finish_interview", "id": "bad-ready", "args": summary},
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "ask_user_question", "id": "ask", "args": {"questions": [question()]}}
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "finish_interview", "id": "ready", "args": summary},
                    write("same-turn"),
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "ask_user_question",
                        "id": "later",
                        "args": {"questions": [question()]},
                    }
                ],
            ),
            AIMessage(content="", tool_calls=[write("after")]),
            FINAL,
        ]
    )
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: model)

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(
            RunRequest(task="/grill task", workspace=str(tmp_path), mode="auto")
        )
        await wait_for(lambda: manager.questions(run_id))
        record = manager.questions(run_id)[0]
        assert not manager.approvals("pending")
        await manager.answer_question(
            run_id,
            "ask",
            QuestionDecision(
                interrupt_id=record.interrupt_id,
                status="answered",
                answers=[QuestionSelection(question_id="q", option_ids=["a"])],
            ),
        )
        await wait_for(lambda: len(manager.questions(run_id)) == 2)
        later = manager.questions(run_id)[1]
        await manager.answer_question(
            run_id, "later", QuestionDecision(interrupt_id=later.interrupt_id, status="declined")
        )
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        assert not (tmp_path / "early").exists()
        assert not (tmp_path / "same-turn").exists()
        assert (tmp_path / "after").read_text() == "bad"
        await manager.close()

    asyncio.run(scenario())
