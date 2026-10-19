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
from typing import Annotated, Any, NotRequired, cast

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState, PrivateStateAttr, ToolCallRequest
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt
from pydantic import BaseModel, JsonValue

from permissions.review import arguments_digest, prepare_review
from permissions.rules import COMMAND_TOOLS, DELETE_TOOLS, READ_TOOLS, WRITE_TOOLS, RulesEngine
from permissions.types import (
    ApprovalAnswer,
    ApprovalBatch,
    ApprovalBatchAnswer,
    ApprovalRequest,
    PermissionOutcome,
)
from questions.types import (
    HumanBatch,
    HumanBatchAnswer,
    QuestionAnswer,
    QuestionInput,
    QuestionRequest,
)
from store.effects import EffectJournal
from store.secrets import Redactor
from tools.jail import JailError, jail_message, resolve_virtual, storage_path

PATH_KEYS = ("file_path", "path", "target_path", "source_path", "destination_path")
"""Argument names the filesystem tools use for the path they act on."""


class PermissionState(AgentState[Any]):
    """Carries the per-turn resolution from the model node to the tools node."""

    permission_outcomes: NotRequired[Annotated[dict[str, dict[str, Any]], PrivateStateAttr]]
    question_outcomes: NotRequired[Annotated[dict[str, dict[str, Any]], PrivateStateAttr]]
    """`tool_call_id -> {action, reason}`. Private: the renderer never sees it."""


def tool_target(tool: str, args: dict[str, Any]) -> tuple[str | None, str | None, float | None]:
    """Split a tool call into the (path, command, timeout) the rules engine needs.

    A command tool contributes its command text; a path tool contributes the first
    path-shaped argument it declares. Tools with neither (for example a future
    `web_search`) contribute nothing and are classified by name alone.
    """
    if tool == "run_command":
        command = args.get("command")
        timeout = args.get("timeout")
        return (
            None,
            str(command) if command is not None else None,
            (float(timeout) if isinstance(timeout, int | float) else None),
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

    def __init__(
        self, rules: RulesEngine, *, run_id: str, redactor: Redactor | None = None
    ) -> None:
        super().__init__()
        self.rules = rules
        self.run_id = run_id
        self.redactor = redactor or Redactor()

    # -- resolution --------------------------------------------------------
    def decide(self, call: ToolCall) -> PermissionOutcome:
        if call["name"] == "ask_user_question":
            return PermissionOutcome(action="allow", reason="human information request")
        path, command, timeout = tool_target(call["name"], call.get("args") or {})
        return self.rules.decide(call["name"], path=path, command=command, timeout=timeout)

    def approval(self, call: ToolCall, outcome: PermissionOutcome) -> ApprovalRequest:
        path, command, timeout = tool_target(call["name"], call.get("args") or {})
        request = ApprovalRequest(
            approval_id=call_key(call),
            run_id=self.run_id,
            kind="command" if call["name"] in COMMAND_TOOLS else "tool",
            tool=call["name"],
            path=path,
            command=command,
            args=call.get("args") or {},
            workspace=str(self.rules.root),
            risk=outcome.risk,
            reason=(
                f"{outcome.reason}. Requested timeout: {timeout:g}s"
                if timeout is not None
                else outcome.reason
            ),
        )
        try:
            request = prepare_review(self.rules.root, request)
        except (ValueError, OSError):
            pass
        return ApprovalRequest.model_validate(self.redactor.value(request.model_dump(mode="json")))

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
                action="allow",
                reason="approved by the user",
                risk=outcome.risk,
                edited_args=answer.edited_args,
                revision=answer.revision or request.revision,
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
        questions: list[QuestionRequest] = []
        invalid: set[str] = set()
        for call in last.tool_calls:
            if call["name"] == "ask_user_question":
                try:
                    args = QuestionInput.model_validate(call["args"])
                    request = QuestionRequest(
                        run_id=self.run_id, call_id=call_key(call), **args.model_dump()
                    )
                    questions.append(
                        QuestionRequest.model_validate(
                            self.redactor.value(request.model_dump(mode="json"))
                        )
                    )
                except ValueError:
                    invalid.add(call_key(call))
        pending = [
            self.approval(call, self.decide(call))
            for call in last.tool_calls
            if self.decide(call).action == "ask"
        ]
        answers: dict[str, ApprovalAnswer] = {}
        question_answers: dict[str, QuestionAnswer] = {}
        if questions:
            response_human = HumanBatchAnswer.model_validate(
                interrupt(
                    HumanBatch(approvals=pending, questions=questions).model_dump(mode="json")
                )
            )
            if set(response_human.approvals) != {item.approval_id for item in pending} or set(
                response_human.questions
            ) != {item.call_id for item in questions}:
                raise ValueError("Human answers do not match the barrier")
            answers = response_human.approvals
            question_answers = response_human.questions
            for question in questions:
                question_answers[question.call_id].validate_request(question)
        elif len(pending) > 1:
            response = ApprovalBatchAnswer.model_validate(
                interrupt(ApprovalBatch(approvals=pending).model_dump(mode="json"))
            )
            if set(response.answers) != {item.approval_id for item in pending}:
                raise ValueError("Approval batch does not match pending calls")
            answers = response.answers
        for call in last.tool_calls:
            outcome = self.decide(call)
            if call_key(call) in invalid:
                outcome = PermissionOutcome(action="deny", reason="Invalid question schema")
            if outcome.action == "ask":
                # One interrupt per call, so the modal never has to present a batch and
                # an answer always names exactly one approval id.
                if answers:
                    answer = answers[call_key(call)]
                    if answer.approval_id != call_key(call):
                        outcome = PermissionOutcome(action="deny", reason="approval mismatch")
                    else:
                        outcome = PermissionOutcome(
                            action="allow" if answer.decision == "approve" else "deny",
                            reason="approved by the user"
                            if answer.decision == "approve"
                            else f"rejected by the user: {answer.reason or ''}",
                            risk=outcome.risk,
                            edited_args=answer.edited_args,
                            revision=answer.revision
                            or next(
                                item.revision
                                for item in pending
                                if item.approval_id == call_key(call)
                            ),
                        )
                else:
                    outcome = self._ask(call, outcome)
            outcomes[call_key(call)] = {
                "action": outcome.action,
                "reason": outcome.reason,
                "risk": outcome.risk.model_dump(),
                "edited_args": outcome.edited_args,
                "revision": outcome.revision,
            }
        return {
            "permission_outcomes": outcomes,
            "question_outcomes": {
                key: answer.model_dump(mode="json") for key, answer in question_answers.items()
            },
        }

    # -- enforcement -------------------------------------------------------
    def refusal(self, call: ToolCall, reason: str) -> ToolMessage:
        return ToolMessage(
            content=(
                f"Permission denied: {self.redactor.text(reason)}. The tool did not run. "
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
        if call["name"] == "ask_user_question":
            value = (state.get("question_outcomes") or {}).get(call_key(call))
            if value is None:
                return self.refusal(call, "No validated human answer")
            answer = QuestionAnswer.model_validate(value)
            answer.validate_request(
                QuestionRequest(
                    run_id=self.run_id,
                    call_id=call_key(call),
                    **QuestionInput.model_validate(call["args"]).model_dump(),
                )
            )
            return ToolMessage(
                content=answer.model_dump_json(), tool_call_id=call_key(call), name=call["name"]
            )
        recorded = (state.get("permission_outcomes") or {}).get(call_key(call))
        if recorded and recorded.get("edited_args") is not None:
            call = {**call, "args": recorded["edited_args"]}
            request = request.override(tool_call=call)
        if recorded is None:
            # Unclassified: decide now and allow only an outright allow.
            outcome = self.decide(call)
            if outcome.action != "allow":
                return self.refusal(call, outcome.reason or "no rule allowed this call")
        elif recorded["action"] == "deny":
            return self.refusal(call, str(recorded.get("reason") or "denied"))
        # Upstream filesystem tools reject Windows absolute paths before calling
        # the backend. Preserve our model/UI jail contract at this outer boundary.
        if call["name"] in READ_TOOLS | WRITE_TOOLS | DELETE_TOOLS:
            path, _, _ = tool_target(call["name"], call.get("args") or {})
            if path:
                try:
                    resolve_virtual(self.rules.root, path)
                except JailError:
                    return ToolMessage(
                        content=jail_message(self.rules.root, path),
                        tool_call_id=call_key(call),
                        name=call["name"],
                    )
        effect = call["name"] in WRITE_TOOLS | DELETE_TOOLS | COMMAND_TOOLS
        if (
            request.tool is not None
            and isinstance(request.tool.args_schema, type)
            and issubclass(request.tool.args_schema, BaseModel)
        ):
            try:
                request.tool.args_schema.model_validate(call["args"])
            except ValueError:
                return self.refusal(call, "Invalid tool arguments")
        journal = EffectJournal(storage_path(self.rules.root, f"runs/{self.run_id}/effects.json"))
        if effect:
            previous = journal.read().get(call_key(call))
            if previous:
                return ToolMessage(
                    content=previous.result
                    or (
                        "Interrupted: this action may have run before the engine stopped. "
                        "It was not replayed. Inspect its effects before requesting a fresh call."
                    ),
                    tool_call_id=call_key(call),
                    name=call["name"],
                )
            current_rules = RulesEngine.load(self.rules.root, self.rules.mode)
            path, command, timeout = tool_target(call["name"], call["args"])
            verdict = current_rules.decide(
                call["name"], path=path, command=command, timeout=timeout
            )
            if verdict.action == "deny":
                return self.refusal(call, verdict.reason)
            if verdict.action == "ask" and (
                not recorded or recorded.get("reason") != "approved by the user"
            ):
                return self.refusal(call, "Permissions changed; request a fresh approval")
            if recorded and recorded.get("revision"):
                review = prepare_review(self.rules.root, self.approval(call, verdict))
                if review.revision != recorded["revision"]:
                    return self.refusal(call, "Reviewed contents changed; request a fresh review")
            journal.begin(call_key(call), arguments_digest(call["args"]))
        result = await handler(request)
        if isinstance(result, ToolMessage):
            result = result.model_copy(
                update={"content": self.redactor.value(cast(JsonValue, result.content))}
            )
            if effect:
                journal.complete(call_key(call), str(result.content))
        return result


def call_key(call: ToolCall) -> str:
    """Stable approval id: the model's tool call id, which survives a resume."""
    return str(call.get("id") or "")
