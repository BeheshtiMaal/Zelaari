"""Tools outside the phase's surface return a readable error instead of crashing the run."""

import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.factory import build_agent
from providers.demo import DemoModel
from store.secrets import Redactor


class ForgedToolModel(DemoModel):
    requested_name: str
    requested_args: dict[str, object] = {}

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="Tool outcome observed")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": self.requested_name,
                    "args": self.requested_args,
                    "id": "forged-call",
                    "type": "tool_call",
                }
            ],
        )


async def _run(tmp_path: Path, model: DemoModel) -> list[ToolMessage]:
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "test.sqlite")) as saver:
        graph = build_agent(tmp_path, model, saver, Redactor())
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": "Probe tool dispatch"}]},
            {"configurable": {"thread_id": "forged"}},
        )
        return [message for message in result["messages"] if isinstance(message, ToolMessage)]


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("execute", {"command": "echo must-not-run"}),
    ],
)
def test_tools_outside_the_surface_are_denied(
    tmp_path: Path, name: str, args: dict[str, object]
) -> None:
    replies = asyncio.run(_run(tmp_path, ForgedToolModel(requested_name=name, requested_args=args)))
    assert replies and replies[0].status == "error"
    assert not (tmp_path / "forbidden.txt").exists()


def test_enabled_tool_names_match_the_phase_surface() -> None:
    from agent.factory import FS_TOOLS

    assert set(FS_TOOLS) == {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "delete",
        "glob",
        "grep",
    }
    assert "execute" not in FS_TOOLS


def test_write_file_is_part_of_the_surface(tmp_path: Path) -> None:
    model = ForgedToolModel(
        requested_name="write_file",
        requested_args={"file_path": "forbidden.txt", "content": "written by the agent"},
    )
    replies = asyncio.run(_run(tmp_path, model))
    assert replies and replies[0].status != "error"
    assert (tmp_path / "forbidden.txt").read_text(encoding="utf-8") == "written by the agent"
