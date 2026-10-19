"""Structural deviations are reviewed under Ask and Auto in the real graph."""

import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from test_permissions import FINAL, ScriptedModel

from agent.factory import build_agent
from permissions.middleware import PermissionMiddleware
from permissions.rules import RulesEngine
from permissions.types import Mode
from store.secrets import Redactor


def propose(count: int) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "submit_plan",
                "id": f"p{count}",
                "args": {"steps": [{"id": f"s{n}", "title": f"Step {n}"} for n in range(count)]},
            }
        ],
    )


@pytest.mark.parametrize("mode", ["ask", "auto"])
@pytest.mark.parametrize("drop", [False, True])
def test_cumulative_additions_or_drop_pause_and_rejection_keeps_plan(
    tmp_path: Path, mode: Mode, drop: bool
) -> None:
    async def scenario() -> None:
        turns = [propose(3), propose(2)] if drop else [propose(n) for n in range(1, 5)]
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "revision.sqlite")) as saver:
            graph = build_agent(
                tmp_path,
                ScriptedModel(replies=[*turns, FINAL]),
                saver,
                Redactor(),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, mode), run_id="run"),
            )
            config: RunnableConfig = {"configurable": {"thread_id": "revision"}}
            paused = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Plan"}]}, config
            )
            review = paused["__interrupt__"][0]
            assert ("dropped_step" if drop else "added_steps") in review.value["reason"]
            assert (
                len((await graph.aget_state(config)).values["plan_record"]["submission"]["steps"])
                == 3
            )
            await graph.ainvoke(
                Command(
                    resume={
                        review.id: {
                            "approval_id": "p2" if drop else "p4",
                            "decision": "reject",
                            "reason": "Keep scope",
                        }
                    }
                ),
                config,
            )
            checkpoint = (await graph.aget_state(config)).values
            assert len(checkpoint["plan_record"]["submission"]["steps"]) == 3
            assert len(checkpoint["plan_record"]["baseline_ids"]) == (3 if drop else 1)

    asyncio.run(scenario())
