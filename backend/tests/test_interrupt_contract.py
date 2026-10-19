"""Installed LangGraph contract: a batch barrier survives SQLite reconstruction."""

import asyncio
from pathlib import Path
from typing import Any, TypedDict

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from permissions.types import ApprovalBatch, ApprovalBatchAnswer, ApprovalRequest
from questions.types import HumanBatch, HumanBatchAnswer, QuestionRequest


class ContractState(TypedDict):
    decisions: dict[str, str]


def test_sqlite_interrupt_id_batch_mapping_and_reconstruction(tmp_path: Path) -> None:
    requests = [
        ApprovalRequest(approval_id=key, run_id="run", kind="tool", tool="write_file")
        for key in ("first", "second")
    ]

    def review(state: ContractState) -> dict[str, Any]:
        answer = ApprovalBatchAnswer.model_validate(
            interrupt(ApprovalBatch(approvals=requests).model_dump(mode="json"))
        )
        assert set(answer.answers) == {"first", "second"}
        assert all(key == value.approval_id for key, value in answer.answers.items())
        return {"decisions": {key: value.decision for key, value in answer.answers.items()}}

    builder = StateGraph(ContractState)
    builder.add_node("review", review)
    builder.add_edge(START, "review")
    builder.add_edge("review", END)
    config: RunnableConfig = {"configurable": {"thread_id": "run"}}

    async def scenario() -> None:
        path = str(tmp_path / "checkpoint.sqlite")
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            graph = builder.compile(checkpointer=saver)
            paused = await graph.ainvoke({"decisions": {}}, config)
            first = paused["__interrupt__"][0]
            assert len(first.value["approvals"]) == 2
            identity = first.id
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            graph = builder.compile(checkpointer=saver)
            restored = await graph.aget_state(config)
            assert restored.interrupts[0].id == identity
            result = await graph.ainvoke(
                Command(
                    resume={
                        identity: {
                            "answers": {
                                "second": {"approval_id": "second", "decision": "reject"},
                                "first": {"approval_id": "first", "decision": "approve"},
                            }
                        }
                    }
                ),
                config,
            )
            assert result["decisions"] == {"second": "reject", "first": "approve"}
            assert not (await graph.aget_state(config)).next

    asyncio.run(scenario())


@pytest.mark.parametrize("reviewed_tool", ["write_file", "submit_plan"])
def test_mixed_barrier_sqlite_reconstruction(tmp_path: Path, reviewed_tool: str) -> None:
    request = QuestionRequest.model_validate(
        {
            "run_id": "run",
            "call_id": "question",
            "questions": [
                {
                    "id": "q",
                    "header": "Approach",
                    "text": "Choose",
                    "type": "single",
                    "options": [
                        {"id": key, "label": key, "description": "Detail"} for key in ("a", "b")
                    ],
                }
            ],
        }
    )
    batch = HumanBatch(
        questions=[request],
        approvals=[
            ApprovalRequest(approval_id="write", run_id="run", kind="tool", tool=reviewed_tool)
        ],
    )

    def review(state: ContractState) -> dict[str, Any]:
        answer = HumanBatchAnswer.model_validate(interrupt(batch.model_dump(mode="json")))
        answer.questions["question"].validate_request(request)
        return {
            "decisions": {
                "write": answer.approvals["write"].decision,
                "question": answer.questions["question"].status,
            }
        }

    builder = StateGraph(ContractState)
    builder.add_node("review", review)
    builder.add_edge(START, "review")
    builder.add_edge("review", END)
    config: RunnableConfig = {"configurable": {"thread_id": "mixed"}}

    async def scenario() -> None:
        path = str(tmp_path / "mixed.sqlite")
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            paused = await builder.compile(checkpointer=saver).ainvoke({"decisions": {}}, config)
            identity = paused["__interrupt__"][0].id
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            graph = builder.compile(checkpointer=saver)
            assert (await graph.aget_state(config)).interrupts[0].id == identity
            result = await graph.ainvoke(
                Command(
                    resume={
                        identity: {
                            "kind": "human",
                            "approvals": {"write": {"approval_id": "write", "decision": "reject"}},
                            "questions": {
                                "question": {
                                    "run_id": "run",
                                    "call_id": "question",
                                    "interrupt_id": identity,
                                    "status": "declined",
                                }
                            },
                        }
                    }
                ),
                config,
            )
            assert result["decisions"] == {"write": "reject", "question": "declined"}

    asyncio.run(scenario())
