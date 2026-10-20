"""Actual plan/question barrier and edited plan previews survive reconstruction."""

import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from pydantic import JsonValue

from agent.bridge import RunManager
from agent.events import RunRequest
from permissions.types import ApprovalDecision, UnknownApproval
from providers.demo import DemoModel
from providers.question_demo import sample_question
from questions.types import QuestionDecision
from store.catalog import Catalog


class MixedPlanModel(DemoModel):
    mixed: bool = True

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(item, ToolMessage) for item in messages):
            return AIMessage(content="Decision observed")
        calls = [
            {
                "name": "submit_plan",
                "id": "plan",
                "args": {"steps": [{"id": f"s{n}", "title": f"Step {n}"} for n in range(4)]},
            }
        ]
        if self.mixed:
            calls.append(
                {
                    "name": "ask_user_question",
                    "id": "question",
                    "args": {"questions": [sample_question()]},
                }
            )
        return AIMessage(content="", tool_calls=calls)


async def until(predicate: Callable[[], object]) -> None:
    async with asyncio.timeout(15):
        while not predicate():
            await asyncio.sleep(0.01)


@pytest.mark.parametrize("question_first", [True, False])
def test_plan_question_partial_decisions_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, question_first: bool
) -> None:
    monkeypatch.setattr("agent.bridge.DemoModel", lambda **kwargs: MixedPlanModel(delay=0))

    async def scenario() -> None:
        root = tmp_path / "project"
        root.mkdir()
        path = tmp_path / "catalog.json"
        manager = RunManager(catalog=Catalog(path))
        run_id = await manager.start(RunRequest(task="Plan and ask", workspace=str(root)))
        await until(lambda: manager.questions(run_id))
        question = manager.questions(run_id)[0]
        answer = QuestionDecision(interrupt_id=question.interrupt_id, status="declined")
        if question_first:
            await manager.answer_question(run_id, "question", answer)
        else:
            await manager.resolve(run_id, "plan", ApprovalDecision(decision="approve"))
        assert not any(event.type == "tool.result" for event in manager.runs[run_id].bus.history)
        await manager.close()
        restored = RunManager(catalog=Catalog(path))
        await restored.recover()
        if question_first:
            await restored.resolve(run_id, "plan", ApprovalDecision(decision="approve"))
        else:
            await restored.answer_question(run_id, "question", answer)
        await until(lambda: restored.runs[run_id].bus.finished)
        events = restored.runs[run_id].bus.history
        assert sum(event.type == "approval.requested" for event in events) == 1
        assert sum(event.type == "question.asked" for event in events) == 1
        assert sum(event.type == "tool.result" for event in events) == 2
        plans = [event for event in events if event.type == "plan.created"]
        assert len(plans) == 1
        assert plans[0].plan.adoption == "approved"
        assert plans[0].seq < next(event.seq for event in events if event.type == "tool.result")
        assert restored.questions(run_id)[0].status == "declined"
        await restored.close()

    asyncio.run(scenario())


def test_edited_plan_preview_binds_exact_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "agent.bridge.DemoModel", lambda **kwargs: MixedPlanModel(delay=0, mixed=False)
    )

    async def scenario() -> None:
        manager = RunManager(catalog=Catalog(tmp_path / "catalog.json"))
        run_id = await manager.start(
            RunRequest(task="Plan", workspace=str(tmp_path), mode="read-only")
        )
        await until(lambda: manager.approvals("pending"))
        before = manager.approvals("pending")[0].request
        assert before.plan_proposed and "Step 3" in str(before.plan_proposed)
        assert before.plan_file_scope is not None
        edited: dict[str, JsonValue] = {
            "steps": [{"id": "revised", "title": "Human edited", "verify_command": "pytest"}]
        }
        review = manager.preview(
            run_id, "plan", ApprovalDecision(decision="approve", edited_args=edited)
        )
        assert review.revision != before.revision
        assert review.plan_proposed and "Human edited" in str(review.plan_proposed)
        assert "Human edited" in review.diff
        with pytest.raises(UnknownApproval):
            await manager.resolve(
                run_id, "plan", ApprovalDecision(decision="approve", revision=before.revision)
            )
        await manager.resolve(
            run_id, "plan", ApprovalDecision(decision="approve", revision=review.revision)
        )
        await until(lambda: manager.runs[run_id].bus.finished)
        assert manager.runs[run_id].bus.history[-1].type == "run.finished"
        assert any(
            event.type == "tool.result"
            and event.call_id == "plan"
            and "Plan accepted" in event.text
            for event in manager.runs[run_id].bus.history
        )
        assert not (tmp_path / "pytest").exists()
        await manager.close()

    asyncio.run(scenario())
