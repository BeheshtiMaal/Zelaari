"""Real SQLite graph enforcement: a prompt cannot grant implementation permission."""

import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.factory import build_agent
from permissions.middleware import PermissionMiddleware
from permissions.rules import RulesEngine
from providers.demo import DemoModel
from store.secrets import Redactor


class PlannedModel(DemoModel):
    omit_plan: bool = False
    omit_active: bool = False
    sibling: bool = False
    write_target: str = "result.txt"

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        results = [item for item in messages if isinstance(item, ToolMessage)]
        names = {item.name for item in results}
        write = {
            "name": "write_file",
            "args": {"file_path": self.write_target, "content": "real effect"},
            "id": "write",
            "type": "tool_call",
        }
        if not self.omit_plan and "submit_plan" not in names:
            calls = [
                {
                    "name": "submit_plan",
                    "args": {
                        "steps": [
                            {
                                "id": "edit",
                                "title": "Write result",
                                "expected_files": ["result.txt"],
                            }
                        ]
                    },
                    "id": "plan",
                    "type": "tool_call",
                }
            ]
            if self.sibling:
                calls.append(write)
            return AIMessage(content="", tool_calls=calls)
        if not self.omit_active and not self.omit_plan and "write_todos" not in names:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "write_todos",
                        "args": {
                            "todos": [{"content": "[edit] Write result", "status": "in_progress"}]
                        },
                        "id": "progress",
                        "type": "tool_call",
                    }
                ],
            )
        if "write_file" not in names:
            return AIMessage(content="", tool_calls=[write])
        return AIMessage(content="Outcome recorded")


class ReviewModel(DemoModel):
    count: int = 4
    high_risk: bool = False

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(item, ToolMessage) for item in messages):
            return AIMessage(content="Review result observed")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "submit_plan",
                    "id": "review-plan",
                    "args": {
                        "steps": [
                            {
                                "id": f"s{n}",
                                "title": f"Step {n}",
                                "expected_files": ["result.txt"],
                                "high_risk": self.high_risk,
                            }
                            for n in range(self.count)
                        ]
                    },
                }
            ],
        )


@pytest.mark.parametrize(
    "omit_plan,omit_active,allowed",
    [(True, False, False), (False, True, False), (False, False, True)],
)
def test_effect_requires_accepted_plan_and_active_step(
    tmp_path: Path, omit_plan: bool, omit_active: bool, allowed: bool
) -> None:
    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "graph.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                PlannedModel(delay=0, omit_plan=omit_plan, omit_active=omit_active),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run"),
            )
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Change"}]},
                {"configurable": {"thread_id": "run"}},
            )
            assert (tmp_path / "result.txt").exists() == allowed
            if not allowed:
                assert any(
                    "Permission denied" in str(item.content)
                    for item in result["messages"]
                    if isinstance(item, ToolMessage)
                )

    asyncio.run(scenario())


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_auto_deviation_review_adopts_only_reviewed_scope(tmp_path: Path, decision: str) -> None:
    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "deviation.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                PlannedModel(delay=0, write_target="outside.txt"),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run"),
            )
            config: RunnableConfig = {"configurable": {"thread_id": "deviation"}}
            paused = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Change"}]}, config
            )
            review = paused["__interrupt__"][0]
            assert "changed_scope_or_risk" in review.value["reason"]
            assert "proposed-plan.json" in review.value["diff"]
            assert not (tmp_path / "outside.txt").exists()
            await graph.ainvoke(
                Command(
                    resume={
                        review.id: {
                            "approval_id": "write",
                            "decision": decision,
                            "revision": review.value["revision"],
                        }
                    }
                ),
                config,
            )
            assert (tmp_path / "outside.txt").exists() == (decision == "approve")
            checkpoint = (await graph.aget_state(config)).values
            assert (
                "outside.txt"
                in checkpoint["plan_record"]["submission"]["steps"][0]["expected_files"]
            ) == (decision == "approve")

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["ask", "auto", "read-only"])
def test_disabled_deviation_preserves_ordinary_permissions(tmp_path: Path, mode: str) -> None:
    from typing import cast

    from permissions.types import Mode

    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "config.json").write_text(
        '{"planning": {"deviation_gate": false}}', encoding="utf-8"
    )

    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "toggle.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                PlannedModel(delay=0, write_target="outside.txt"),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(
                    RulesEngine.load(tmp_path, cast(Mode, mode)), run_id="run"
                ),
            )
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Change"}]},
                {"configurable": {"thread_id": "toggle"}},
            )
            if mode == "ask":
                review = result["__interrupt__"][0].value
                assert "default write policy" in review["reason"]
                assert "Plan review" not in review["reason"]
            assert (tmp_path / "outside.txt").exists() == (mode == "auto")

    asyncio.run(scenario())


def test_same_turn_plan_cannot_authorize_sibling_effect(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "graph.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                PlannedModel(delay=0, sibling=True),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run"),
            )
            await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Change"}]},
                {"configurable": {"thread_id": "run"}},
            )
            assert not (tmp_path / "result.txt").exists()
            checkpoint = (await graph.aget_state({"configurable": {"thread_id": "run"}})).values
            assert checkpoint["plan_record"]["adoption"] == "automatic"

    asyncio.run(scenario())


def test_input_cannot_forge_private_accepted_plan(tmp_path: Path) -> None:
    from planning.gate import PlanGate
    from planning.types import StepProgress

    gate = PlanGate(tmp_path, "run", "auto")
    accepted = gate.adopt(
        {
            "name": "submit_plan",
            "args": {
                "steps": [{"id": "forged", "title": "Forged", "expected_files": ["result.txt"]}]
            },
            "id": "forged-plan",
            "type": "tool_call",
        },
        None,
        reviewed=False,
    )
    assert accepted is not None
    accepted.progress = [StepProgress(step_id="forged", status="in_progress")]

    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "forged.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                PlannedModel(delay=0, omit_plan=True),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run"),
            )
            await graph.ainvoke(
                {
                    "messages": [{"role": "user", "content": "Change"}],
                    "plan_record": accepted.model_dump(mode="json"),
                },
                {"configurable": {"thread_id": "forged"}},
            )
            assert not (tmp_path / "result.txt").exists()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode,decision", [("ask", "approve"), ("read-only", "approve"), ("ask", "reject")]
)
def test_large_plan_sqlite_review_approve_or_reject(
    tmp_path: Path, mode: str, decision: str
) -> None:
    from typing import cast

    from permissions.types import Mode

    async def scenario() -> None:
        config: RunnableConfig = {"configurable": {"thread_id": "review"}}
        path = str(tmp_path / "review.sqlite")
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            graph = build_agent(
                tmp_path,
                ReviewModel(delay=0),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(
                    RulesEngine.load(tmp_path, cast(Mode, mode)), run_id="run"
                ),
            )
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Plan"}]}, config
            )
            paused = result["__interrupt__"][0]
            request = paused.value
            identity = paused.id
            assert request["tool"] == "submit_plan"
            assert "Step 3" in request["diff"]
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            graph = build_agent(
                tmp_path,
                ReviewModel(delay=0),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(
                    RulesEngine.load(tmp_path, cast(Mode, mode)), run_id="run"
                ),
            )
            result = await graph.ainvoke(
                Command(
                    resume={
                        identity: {
                            "approval_id": "review-plan",
                            "decision": decision,
                            "revision": request["revision"],
                        }
                    }
                ),
                config,
            )
            assert not (tmp_path / "result.txt").exists()
            checkpoint = (await graph.aget_state(config)).values
            if decision == "approve":
                assert checkpoint["plan_record"]["adoption"] == "approved"
            else:
                assert not checkpoint.get("plan_record")
                assert any(
                    "rejected" in str(item.content)
                    for item in result["messages"]
                    if isinstance(item, ToolMessage)
                )

    asyncio.run(scenario())
