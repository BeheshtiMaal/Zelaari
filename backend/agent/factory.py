"""The deepagents harness: jailed filesystem tools, `run_command`, one permission gate."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from permissions.middleware import PermissionMiddleware
from questions.tools import build_ask_question, build_finish_interview
from store.secrets import Redactor
from tools.fs import SnapshotSink, WorkspaceBackend

FS_TOOLS: list[Any] = [
    "ls",
    "read_file",
    "write_file",
    "edit_file",
    "delete",
    "glob",
    "grep",
]
"""Stock `execute` stays out: `run_command` owns shell access and its permission path."""


class RedactingMiddleware(AgentMiddleware[Any, Any, Any]):
    """Scrub registered secrets before graph state is checkpointed.

    The event bridge runs after persistence, so redaction has to happen here.
    """

    def __init__(self, redactor: Redactor) -> None:
        self.redactor = redactor

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        response = await handler(request)
        response.result = [
            type(message).model_validate(self.redactor.value(message.model_dump(mode="json")))
            for message in response.result
        ]
        return response


def build_agent(
    root: Path,
    model: BaseChatModel,
    saver: AsyncSqliteSaver,
    redactor: Redactor,
    *,
    permissions: PermissionMiddleware | None = None,
    snapshots: SnapshotSink | None = None,
    extra_tools: list[Any] | None = None,
    extra_middleware: list[AgentMiddleware[Any, Any, Any]] | None = None,
    grill: bool = False,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    backend = WorkspaceBackend(root, redactor, snapshots)
    prompt = Path(__file__).with_name("genui_prompt.txt").read_text(encoding="utf-8")
    return create_deep_agent(
        model=model,
        backend=backend,
        checkpointer=saver,
        system_prompt=(
            "You are CodeHarness, a coding agent working inside one workspace folder. "
            "Use relative paths. Read before you edit. Keep changes small and explain them. "
            "File tools: ls, read_file, write_file, edit_file, delete, glob, grep. "
            "delete removes a single file only; directories need run_command. "
            "run_command runs a shell command in the workspace and returns exit code, "
            "duration and at most 200 lines; page with offset. "
            "A call may come back with 'Permission denied': that is a decision, not an "
            "error to retry. Explain it and adjust the plan. "
            "Reply in the user's language. "
            + (
                "This is /grill interview mode. Read project context; ask_user_question one batch "
                "at a time, using earlier answers. Avoid repeating answered questions. "
                "When objective, scope, constraints and acceptance are specified, call "
                "finish_interview with a summary, then continue the original task. Decline ends "
                "the interview: report and do not implement. "
                if grill
                else ""
            )
            + "Your final response must use this UI library:\n"
            + prompt
        ),
        tools=[
            build_ask_question(),
            *([build_finish_interview()] if grill else []),
            *(extra_tools or []),
        ],
        middleware=cast(
            list[AgentMiddleware[Any, Any, Any]],
            [
                # First is outermost: the permission gate must see every tool call
                # before anything else can execute it.
                *([permissions] if permissions else []),
                TodoListMiddleware(),
                FilesystemMiddleware(
                    backend=backend,
                    tools=FS_TOOLS,
                    tool_token_limit_before_evict=None,
                    human_message_token_limit_before_evict=None,
                ),
                RedactingMiddleware(redactor),
                *(extra_middleware or []),
            ],
        ),
    )
