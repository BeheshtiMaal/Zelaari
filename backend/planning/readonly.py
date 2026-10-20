"""Independent delegate ceiling, including tools added by future middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from deepagents.backends.protocol import DeleteResult, EditResult, FileUploadResponse, WriteResult
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from tools.fs import WorkspaceBackend

SAFE_READ_TOOLS = frozenset({"ls", "read_file", "glob", "grep"})


class ReadOnlyWorkspaceBackend(WorkspaceBackend):
    """Internal harness operations cannot bypass the child tool ceiling either."""

    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error="Permission denied: read-only delegate backend")

    def edit(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> EditResult:
        return EditResult(error="Permission denied: read-only delegate backend")

    def delete(self, file_path: str) -> DeleteResult:
        return DeleteResult(error="Permission denied: read-only delegate backend")

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return [FileUploadResponse(path=path, error="permission_denied") for path, _ in files]


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
