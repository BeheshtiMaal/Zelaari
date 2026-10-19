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
from questions.types import QuestionDecision, QuestionSelection
from store.catalog import Catalog


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
        await wait_for(lambda: manager.runs[run_id].bus.finished)
        assert not (tmp_path / "early").exists()
        assert not (tmp_path / "same-turn").exists()
        assert (tmp_path / "after").read_text() == "bad"
        await manager.close()

    asyncio.run(scenario())
