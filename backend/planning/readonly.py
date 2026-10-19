"""Independent delegate ceiling, including tools added by future middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

SAFE_READ_TOOLS = frozenset({"ls", "read_file", "glob", "grep"})


class ReadOnlyDelegateMiddleware(AgentMiddleware[Any, Any, Any]):
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        if request.tool_call["name"] not in SAFE_READ_TOOLS:
            return ToolMessage(
                content="Permission denied: delegated agents can only read workspace context.",
                tool_call_id=request.tool_call["id"],
                name=request.tool_call["name"],
                status="error",
            )
        return await handler(request)
