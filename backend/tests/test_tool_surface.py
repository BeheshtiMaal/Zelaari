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

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content="Denied tool observed")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": self.requested_name,
                    "args": {
                        "file_path": "forbidden.txt",
                        "content": "must not be written",
                        "command": "echo must-not-run",
                        "description": "must not delegate",
                        "subagent_type": "general-purpose",
                    },
                    "id": "forged-call",
                    "type": "tool_call",
                }
            ],
        )


@pytest.mark.parametrize("name", ["write_file", "edit_file", "execute", "run_command", "task"])
def test_forged_out_of_scope_tools_are_denied(tmp_path: Path, name: str) -> None:
    async def scenario() -> None:
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "test.sqlite")) as saver:
            graph = build_agent(
                tmp_path, ForgedToolModel(requested_name=name, delay=0), saver, Redactor()
            )
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Probe tool dispatch"}]},
                {"configurable": {"thread_id": name}},
            )
            replies = [
                message for message in result["messages"] if isinstance(message, ToolMessage)
            ]
            assert replies and replies[0].status == "error"
            assert not (tmp_path / "forbidden.txt").exists()

    asyncio.run(scenario())
