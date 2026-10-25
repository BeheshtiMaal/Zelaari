"""Engine-owned turn and delegate identities, shared by graph and event projection."""

import hashlib
import json
import math
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Annotated, Any, NotRequired
from uuid import uuid4

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import (
    AgentState,
    ModelRequest,
    ModelResponse,
    PrivateStateAttr,
    ToolCallRequest,
)
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from planning.gate import record_from_state
from planning.progress import active_step
from planning.types import ActivityScope
from store.delegates import DelegateResults
from store.eventlog import EventBus

delegate_scope: ContextVar[ActivityScope | None] = ContextVar("delegate_scope", default=None)

DELEGATES: frozenset[str] = frozenset({"reviewer", "researcher"})
"""The built-in read-only delegates; a workspace agent is added to this set per run."""


def identity(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:32]


class ActivityState(AgentState[Any]):
    activity_scope: NotRequired[Annotated[dict[str, Any], PrivateStateAttr]]
    child_activity_scope: NotRequired[dict[str, Any]]


class ActivityMiddleware(AgentMiddleware[ActivityState, Any, Any]):
    state_schema = ActivityState

    def __init__(
        self,
        model: str,
        agent: str = "parent",
        bus: EventBus | None = None,
        provider: str | None = None,
        delegates: frozenset[str] | None = None,
    ) -> None:
        self.model = model
        self.agent = agent
        self.bus = bus
        self.provider = provider
        self.delegates = delegates or DELEGATES
        self.results = (
            DelegateResults(bus.path.with_name("delegates.json"), bus.redactor) if bus else None
        )

    async def abefore_model(self, state: ActivityState, runtime: Runtime[Any]) -> dict[str, Any]:
        parent = delegate_scope.get() if self.agent != "parent" else None
        plan = record_from_state(dict(state)) if self.agent == "parent" else None
        step = active_step(plan) if plan else None
        turn = uuid4().hex
        scope = ActivityScope(
            scope_id=turn,
            turn_id=turn,
            step_id=parent.step_id if parent else step.id if step else None,
            parent_scope_id=parent.scope_id if parent else None,
            agent=self.agent,
            model=self.model,
            provider=self.provider,
        )
        return {
            "activity_scope"
            if self.agent == "parent"
            else "child_activity_scope": scope.model_dump(mode="json"),
        }

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        call = request.tool_call
        if call["name"] != "task":
            return await handler(request)
        if self.bus is None:
            result = await handler(request)
            if isinstance(result, Command) and isinstance(result.update, dict):
                result.update.pop("child_activity_scope", None)
                result.update.pop("summary_notice", None)
            return result
        args = call["args"]
        name = args.get("subagent_type")
        if name not in self.delegates:
            return ToolMessage(
                content="Permission denied: unknown delegate", tool_call_id=call["id"]
            )
        parent = ActivityScope.model_validate(request.state["activity_scope"])
        invocation = identity(self.bus.run_id + str(call["id"]))
        arguments = identity(json.dumps(args, sort_keys=True))
        if self.results and invocation in self.results.records:
            if self.results.records[invocation].arguments_digest != arguments:
                return ToolMessage(
                    content="Permission denied: delegate call identity reused",
                    tool_call_id=call["id"],
                    status="error",
                )
            return ToolMessage(
                content=self.results.records[invocation].text, tool_call_id=call["id"]
            )
        attempts = sum(
            event.type == "subagent.started" and event.scope.invocation_id == invocation
            for event in self.bus.history
        )
        scope = ActivityScope(
            scope_id=identity(invocation + str(attempts)),
            invocation_id=invocation,
            step_id=parent.step_id,
            parent_scope_id=parent.scope_id,
            agent=name,
            model=self.model,
            provider=self.provider,
        )
        completed = next(
            (
                e
                for e in reversed(self.bus.history)
                if e.type == "subagent.finished"
                and e.scope.scope_id == scope.scope_id
                and e.status == "completed"
            ),
            None,
        )
        if completed:
            return ToolMessage(content=completed.result or "", tool_call_id=call["id"])
        await self.bus.emit("subagent.started", scope=scope, task=str(args.get("description", "")))
        token = delegate_scope.set(scope)
        try:
            result = await handler(request)
            if isinstance(result, Command) and isinstance(result.update, dict):
                result.update.pop("child_activity_scope", None)
                result.update.pop("summary_notice", None)
            messages = (
                (result.update or {}).get("messages", [])
                if isinstance(result, Command)
                else [result]
            )
            text = str(messages[-1].content) if messages else ""
            if self.results:
                self.results.complete(invocation, scope, text, arguments)
            return result
        finally:
            delegate_scope.reset(token)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        # This is inside the summarizer, so it observes the effective request.
        messages = [*request.messages]
        if request.system_message:
            messages.insert(0, request.system_message)
        characters = sum(len(m.model_dump_json()) for m in messages)
        characters += sum(
            len(json.dumps(t.args)) if hasattr(t, "args") else len(str(t)) for t in request.tools
        )
        response = await handler(request)
        for message in response.result:
            if isinstance(message, AIMessage):
                message.additional_kwargs["_harness_input_tokens"] = max(
                    1, math.ceil(characters / 4)
                )
        return response


def open_activity(bus: EventBus) -> list[tuple[str, ActivityScope]]:
    opened: dict[str, tuple[str, ActivityScope]] = {}
    for event in bus.history:
        if event.type in {"activity.started", "subagent.started"}:
            opened[event.scope.scope_id] = (event.type, event.scope)
        elif event.type in {"activity.finished", "subagent.finished"}:
            opened.pop(event.scope.scope_id, None)
    return list(reversed(list(opened.values())))


async def finish_open_activity(bus: EventBus, status: str) -> None:
    """Reconcile an interrupted process or Stop without inventing successful work."""
    for kind, scope in open_activity(bus):
        if kind == "subagent.started" and status == "interrupted":
            results = DelegateResults(bus.path.with_name("delegates.json"), bus.redactor)
            result = results.records.get(scope.invocation_id or "")
            if result and result.scope.scope_id == scope.scope_id:
                await bus.emit(
                    "subagent.finished", scope=scope, status="completed", result=result.text
                )
                continue
        await bus.emit(kind.replace("started", "finished"), scope=scope, status=status)
