"""Production factory: concurrent jailed children, no inherited mutation authority."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from deepagents.backends.protocol import ReadResult
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.factory import build_agent
from permissions.middleware import PermissionMiddleware
from permissions.rules import RulesEngine
from planning.readonly import ReadOnlyWorkspaceBackend
from providers.demo import DemoModel
from store.secrets import Redactor
from tools.fs import WorkspaceBackend


class DelegateProbe(DemoModel):
    forbidden: str = "write_file"
    canary: str = "delegate-secret-canary"

    def answer(self, messages: list[BaseMessage]) -> AIMessage:
        child = any(
            isinstance(item, SystemMessage) and "You are the read-only" in str(item.content)
            for item in messages
        )
        results = [item for item in messages if isinstance(item, ToolMessage)]
        if child:
            if not results:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "read_file", "id": "read", "args": {"file_path": "context.txt"}}
                    ],
                )
            if len(results) == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": self.forbidden,
                            "id": "forbidden",
                            "args": {"file_path": "forbidden.txt", "content": "must not write"},
                        }
                    ],
                )
            return AIMessage(
                content="Read context; denied action. " + str(results[0].content) + self.canary
            )
        if results:
            return AIMessage(content="Parent observed read-only delegates")
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "task",
                    "id": name,
                    "args": {
                        "subagent_type": name,
                        "description": "Read context and probe the boundary",
                    },
                }
                for name in ("reviewer", "researcher")
            ],
        )


@pytest.mark.parametrize(
    "forbidden",
    ["write_file", "edit_file", "delete", "run_command", "task", "planning_settings_update"],
)
def test_factory_delegates_read_concurrently_and_deny_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forbidden: str
) -> None:
    (tmp_path / "context.txt").write_text("Actual local context", encoding="utf-8")
    original = WorkspaceBackend.aread

    async def scenario() -> None:
        count = 0
        both = asyncio.Event()

        async def coordinated_read(self: WorkspaceBackend, *args: Any, **kwargs: Any) -> ReadResult:
            nonlocal count
            count += 1
            if count == 2:
                both.set()
            await asyncio.wait_for(both.wait(), 5)
            return await original(self, *args, **kwargs)

        monkeypatch.setattr(WorkspaceBackend, "aread", coordinated_read)
        path = tmp_path / "delegates.sqlite"
        model = DelegateProbe(delay=0, forbidden=forbidden)
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            graph = build_agent(
                tmp_path,
                model,
                saver,
                Redactor([model.canary]),
                permissions=PermissionMiddleware(RulesEngine.load(tmp_path, "auto"), run_id="run"),
            )
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Delegate"}]},
                {"configurable": {"thread_id": "run"}},
            )
            assert count == 2
            assert not (tmp_path / "forbidden.txt").exists()
            outputs = [item for item in result["messages"] if isinstance(item, ToolMessage)]
            assert {item.tool_call_id for item in outputs} == {"reviewer", "researcher"}
            assert all("Read context; denied action." in str(item.content) for item in outputs)
            assert all("Actual local context" in str(item.content) for item in outputs)
            assert all(model.canary not in str(item.content) for item in outputs)
        assert model.canary.encode() not in path.read_bytes()

    asyncio.run(scenario())


def test_internal_backend_operations_cannot_write_behind_child_tools(tmp_path: Path) -> None:
    target = tmp_path / "context.txt"
    target.write_text("Original", encoding="utf-8")
    backend = ReadOnlyWorkspaceBackend(tmp_path, Redactor())

    async def scenario() -> None:
        assert (await backend.awrite("created.txt", "bad")).error
        assert (await backend.aedit("context.txt", "Original", "bad")).error
        assert (await backend.adelete("context.txt")).error
        assert (await backend.aupload_files([("created.txt", b"bad")]))[0].error

    asyncio.run(scenario())
    assert target.read_text(encoding="utf-8") == "Original"
    assert not (tmp_path / "created.txt").exists()
