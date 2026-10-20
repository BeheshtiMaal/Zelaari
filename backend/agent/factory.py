"""The deepagents harness: jailed filesystem tools, `run_command`, one permission gate."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from threading import Event
from typing import Any, Literal, cast
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgentMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, TodoListMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from agent.activity import ActivityMiddleware
from agent.summarization import RedactingSummarization, summary_backend
from permissions.middleware import PermissionMiddleware
from planning.readonly import SAFE_READ_TOOLS, ReadOnlyDelegateMiddleware, ReadOnlyWorkspaceBackend
from planning.tools import build_submit_plan
from questions.tools import build_ask_question, build_finish_interview
from store.eventlog import EventBus
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
        previous_ids = {message.id for message in request.messages if message.id}
        for index, message in enumerate(response.result):
            if isinstance(message, AIMessage) and message.id in previous_ids:
                # Some compatible models reuse response IDs. add_messages would
                # replace an earlier turn and leave a stale tool-call turn last.
                response.result[index] = message.model_copy(update={"id": uuid4().hex})
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
    bus: EventBus | None = None,
    model_name: str | None = None,
    provider_name: str | None = None,
    cancelled: Event | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    backend = WorkspaceBackend(root, redactor, snapshots, cancelled=cancelled)
    child_backend = ReadOnlyWorkspaceBackend(root, redactor)
    prompt = Path(__file__).with_name("genui_prompt.txt").read_text(encoding="utf-8")
    children: list[CompiledSubAgent] = []
    read_tools: list[Any] = sorted(SAFE_READ_TOOLS)
    delegate_names: tuple[Literal["reviewer", "researcher"], ...] = ("reviewer", "researcher")
    for name in delegate_names:
        children.append(
            {
                "name": name,
                "description": "Review source and report findings"
                if name == "reviewer"
                else "Research workspace and local documentation",
                "runnable": create_agent(
                    model=model,
                    system_prompt=(
                        f"You are the read-only {name}. Read workspace files and report findings "
                        "in the user's language. Return clarification needs to the parent."
                    ),
                    middleware=cast(
                        list[AgentMiddleware[Any, Any, Any]],
                        [
                            ReadOnlyDelegateMiddleware(redactor),
                            FilesystemMiddleware(
                                backend=child_backend,
                                tools=read_tools,
                                tool_token_limit_before_evict=None,
                                human_message_token_limit_before_evict=None,
                            ),
                            RedactingMiddleware(redactor),
                            RedactingSummarization(model, child_backend, redactor),
                            ActivityMiddleware(
                                model_name or model.name or type(model).__name__,
                                name,
                                provider=provider_name,
                            ),
                        ],
                    ),
                    name=name,
                ),
            }
        )
    return create_deep_agent(
        model=model,
        backend=backend,
        checkpointer=saver,
        system_prompt=(
            "You are CodeHarness, a coding agent working inside one workspace folder. "
            "Use relative paths. Read before you edit. Keep changes small and explain them. "
            "Analyze first, then submit_plan before mutations or commands. Use stable step IDs and "
            "expected file globs. Track progress via write_todos content '[step_id] title', "
            "with one "
            "in_progress parent step. Follow accepted scope and submit revisions for deviations. "
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
            build_submit_plan(),
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
                RedactingSummarization(model, summary_backend(root, redactor, cancelled), redactor),
                SubAgentMiddleware(backend=backend, subagents=children),
                ActivityMiddleware(
                    model_name or model.name or type(model).__name__,
                    bus=bus,
                    provider=provider_name,
                ),
                *(extra_middleware or []),
            ],
        ),
    )
