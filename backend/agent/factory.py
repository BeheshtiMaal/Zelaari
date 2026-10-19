"""The Phase 1 deepagents harness: actual read dispatch and SQLite checkpoints."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse, ToolCallRequest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from store.secrets import Redactor
from tools.jail import ReadOnlyBackend


class ReadOnlyTools(AgentMiddleware[Any, Any, Any]):
    """Enforce the phase's tool surface even if a model invents a tool call."""

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        tools = [
            tool
            for tool in request.tools
            if getattr(tool, "name", "") in {"read_file", "write_todos"}
        ]
        return await handler(request.override(tools=tools))

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        if request.tool_call["name"] not in {"read_file", "write_todos"}:
            return ToolMessage(
                content="Phase 1 allows file reads only",
                status="error",
                tool_call_id=request.tool_call["id"],
            )
        return await handler(request)


def build_agent(
    root: Path,
    model: BaseChatModel,
    saver: AsyncSqliteSaver,
    redactor: Redactor,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    backend = ReadOnlyBackend(root, redactor)
    prompt = Path(__file__).with_name("genui_prompt.txt").read_text(encoding="utf-8")
    return create_deep_agent(
        model=model,
        backend=backend,
        checkpointer=saver,
        system_prompt=(
            "You are CodeHarness. Read the requested workspace file and summarize it honestly. "
            "Only read_file is available for workspace access. Use relative paths. "
            "Never claim to edit or run commands. Reply in the user's language. "
            "Your final response must use this UI library:\n" + prompt
        ),
        middleware=cast(
            list[AgentMiddleware[Any, Any, Any]],
            [
                TodoListMiddleware(),
                FilesystemMiddleware(
                    backend=backend,
                    tools=["read_file"],
                    tool_token_limit_before_evict=None,
                    human_message_token_limit_before_evict=None,
                ),
                ReadOnlyTools(),
            ],
        ),
    )
