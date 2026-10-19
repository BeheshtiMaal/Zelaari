"""The one authority that decides whether a tool call may run.

The decision is made in `aafter_model`, before the tools node exists, because a
LangGraph `interrupt` re-executes the node that raised it from the start. Raising it
inside `awrap_tool_call` would re-run the sibling tool calls of the same turn, and a
write that already happened would happen twice. This mirrors the installed
`HumanInTheLoopMiddleware`, which interrupts in `after_model` and enforces in
`wrap_tool_call`.

The resolution is written to graph state, keyed by tool call id, so the wrapper only
has to look it up. A call with no recorded resolution is refused rather than run:
the only way to reach the wrapper without one is a tool call this middleware never
classified, and the safe answer to "unclassified" is no.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, NotRequired

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState, PrivateStateAttr, ToolCallRequest
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from permissions.rules import COMMAND_TOOLS, RulesEngine
from permissions.types import ApprovalAnswer, ApprovalRequest, PermissionOutcome

PATH_KEYS = ("file_path", "path", "target_path", "source_path", "destination_path")
"""Argument names the filesystem tools use for the path they act on."""


class PermissionState(AgentState[Any]):
    """Carries the per-turn resolution from the model node to the tools node."""

    permission_outcomes: NotRequired[
        Annotated[dict[str, dict[str, Any]], PrivateStateAttr]
    ]
    """`tool_call_id -> {action, reason}`. Private: the renderer never sees it."""


def tool_target(
    tool: str, args: dict[str, Any]
) -> tuple[str | None, str | None, float | None]:
    """Split a tool call into the (path, command, timeout) the rules engine needs.

    A command tool contributes its command text; a path tool contributes the first
    path-shaped argument it declares. Tools with neither (for example a future
    `web_search`) contribute nothing and are classified by name alone.
    """
    if tool == "run_command":
        command = args.get("command")
        timeout = args.get("timeout")
        return None, str(command) if command is not None else None, (
            float(timeout) if isinstance(timeout, int | float) else None
        )
    if tool == "git_switch":
        branch = args.get("branch")
        return None, f"git switch {branch}" if branch else None, None
    if tool == "worktree_create":
        path = args.get("path") or args.get("name")
        return str(path) if path else None, None, None
    for key in PATH_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value:
            return value, None, None
    return None, None, None


class PermissionMiddleware(AgentMiddleware[Any, Any, Any]):
    """Resolve every tool call against the rules grid, then enforce the answer."""

    state_schema = PermissionState

    def __init__(self, rules: RulesEngine, *, run_id: str) -> None:
        super().__init__()
        self.rules = rules
        self.run_id = run_id

    # -- resolution --------------------------------------------------------
    def decide(self, call: ToolCall) -> PermissionOutcome:
        path, command, timeout = tool_target(call["name"], call.get("args") or {})
        return self.rules.decide(call["name"], path=path, command=command, timeout=timeout)

    def approval(self, call: ToolCall, outcome: PermissionOutcome) -> ApprovalRequest:
        path, command, _timeout = tool_target(call["name"], call.get("args") or {})
        return ApprovalRequest(
            approval_id=call_key(call),
            run_id=self.run_id,
            kind="command" if call["name"] in COMMAND_TOOLS else "tool",
            tool=call["name"],
            path=path,
            command=command,
            risk=outcome.risk,
            reason=outcome.reason,
        )

    def _ask(self, call: ToolCall, outcome: PermissionOutcome) -> PermissionOutcome:
        """Pause for one decision and fold the answer back into an outcome."""
        request = self.approval(call, outcome)
        answer = ApprovalAnswer.model_validate(
            interrupt(request.model_dump(mode="json"), response_schema=ApprovalAnswer)
        )
        if answer.approval_id != request.approval_id:
            # The graph handed back an answer for a different call; refuse rather than
            # apply a stranger's decision.
            return PermissionOutcome(action="deny", reason="approval did not match this call")
        if answer.decision == "approve":
            return PermissionOutcome(
                action="allow", reason="approved by the user", risk=outcome.risk
            )
        detail = f"rejected by the user: {answer.reason}"
        return PermissionOutcome(
            action="deny",
            reason=detail if answer.reason else "rejected by the user",
            risk=outcome.risk,
        )

    async def aafter_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        messages = state.get("messages") or []
        last = next((item for item in reversed(messages) if isinstance(item, AIMessage)), None)
        if last is None or not last.tool_calls:
            return None

        outcomes: dict[str, dict[str, Any]] = {}
        for call in last.tool_calls:
            outcome = self.decide(call)
            if outcome.action == "ask":
                # One interrupt per call, so the modal never has to present a batch and
                # an answer always names exactly one approval id.
                outcome = self._ask(call, outcome)
            outcomes[call_key(call)] = {
                "action": outcome.action,
                "reason": outcome.reason,
                "risk": outcome.risk.model_dump(),
            }
        return {"permission_outcomes": outcomes}

    # -- enforcement -------------------------------------------------------
    def refusal(self, call: ToolCall, reason: str) -> ToolMessage:
        return ToolMessage(
            content=(
                f"Permission denied: {reason}. The tool did not run. "
                "Do not retry the same call; adjust the plan or ask the user."
            ),
            tool_call_id=call_key(call),
            name=call["name"],
        )

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        call = request.tool_call
        state = request.state if isinstance(request.state, dict) else {}
        recorded = (state.get("permission_outcomes") or {}).get(call_key(call))
        if recorded is None:
            # Unclassified: decide now and allow only an outright allow.
            outcome = self.decide(call)
            if outcome.action != "allow":
                return self.refusal(call, outcome.reason or "no rule allowed this call")
            return await handler(request)
        if recorded["action"] == "deny":
            return self.refusal(call, str(recorded.get("reason") or "denied"))
        return await handler(request)


def call_key(call: ToolCall) -> str:
    """Stable approval id: the model's tool call id, which survives a resume."""
    return str(call.get("id") or "")
