"""Installed LangGraph contract: a batch barrier survives SQLite reconstruction."""

import asyncio
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from permissions.types import ApprovalBatch, ApprovalBatchAnswer, ApprovalRequest


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
