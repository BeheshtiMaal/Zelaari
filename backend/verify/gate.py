"""The verify gate: a run may not finish on unverified changes.

The decision is a pure function of the message history — successful tool results, the
verification command's exit code, and the harness's own injections — so it survives a
restart without extra state and can never be satisfied by the model's own claim.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain.agents.middleware.types import AgentState
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from store.eventlog import EventBus
from verify.results import matches_verification

MUTATIONS = {"write_file", "edit_file", "delete"}
VERIFICATION_HEADER = "Verification"
MAX_INJECTIONS = 3
MAX_COMMAND = 400
INJECTED = "verify"

Action = Literal["allow", "block", "ask", "give_up"]


@dataclass(frozen=True)
class GateDecision:
    action: Action
    reason: Literal["ok", "unverified_changes", "no_command", "declined", "gave_up"]
    command: str | None = None
    injections: int = 0


@dataclass(frozen=True)
class Scan:
    pending: bool = False
    injections: int = 0
    adopted: str | None = None
    declined: bool = False


def call_command(args: Any) -> str | None:
    if isinstance(args, dict):
        value = args.get("command")
        if isinstance(value, str) and value.strip():
            return value
    return None


def failed(message: ToolMessage) -> bool:
    """A refusal or a tool-reported error is not a change to the workspace."""
    if message.status == "error":
        return True
    text = str(message.content).lstrip().casefold()
    return text.startswith(("error", "permission denied", "interrupted"))


def verified(message: ToolMessage, command: str | None, verification: str) -> bool:
    if command is None or not matches_verification(command, verification):
        return False
    try:
        payload = json.loads(str(message.content))
    except ValueError:
        return False
    return isinstance(payload, dict) and payload.get("exit_code") == 0


def adopted_command(call: dict[str, Any], message: ToolMessage) -> tuple[str | None, bool]:
    """Read the answer to a `Verification` question: the chosen command, or a decline."""
    try:
        answer = json.loads(str(message.content))
    except ValueError:
        return None, False
    if not isinstance(answer, dict):
        return None, False
    if answer.get("status") == "declined":
        return None, True
    questions = call.get("args", {}).get("questions")
    if not isinstance(questions, list):
        return None, False
    selections = answer.get("answers")
    if not isinstance(selections, list):
        return None, False
    for selection in selections:
        if not isinstance(selection, dict):
            continue
        question = next(
            (
                item
                for item in questions
                if isinstance(item, dict)
                and item.get("id") == selection.get("question_id")
                and str(item.get("header", "")).strip().casefold() == VERIFICATION_HEADER.casefold()
            ),
            None,
        )
        if question is None:
            continue
        other = selection.get("other")
        if isinstance(other, str) and other.strip():
            return other.strip()[:MAX_COMMAND], False
        chosen = selection.get("option_ids")
        options = question.get("options")
        if isinstance(chosen, list) and isinstance(options, list):
            for option in options:
                if isinstance(option, dict) and option.get("id") in chosen:
                    label = str(option.get("label", "")).strip()
                    if label:
                        return label[:MAX_COMMAND], False
    return None, False


def scan(messages: Sequence[Any], verification: str | None) -> Scan:
    calls: dict[str, dict[str, Any]] = {}
    last_mutation = -1
    last_verified = -1
    injections = 0
    adopted: str | None = None
    declined = False
    current = verification
    for index, message in enumerate(messages):
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                if tool_call.get("id"):
                    calls[str(tool_call["id"])] = dict(tool_call)
            continue
        if isinstance(message, HumanMessage):
            if message.additional_kwargs.get("harness") == INJECTED:
                injections += 1
            continue
        if not isinstance(message, ToolMessage):
            continue
        call = calls.get(str(message.tool_call_id), {})
        name = call.get("name") or message.name
        if name in MUTATIONS:
            if not failed(message):
                last_mutation = index
            continue
        if name == "run_command":
            command = call_command(call.get("args"))
            if current and verified(message, command, current):
                # A passing check is the only progress that ends an injection stretch.
                last_verified = index
                injections = 0
            continue
        if name == "ask_user_question":
            command, refused = adopted_command(call, message)
            declined = declined or refused
            # A command the person chose applies from this point on.
            current = command or current
            adopted = current
            continue
    return Scan(
        pending=last_mutation > last_verified,
        injections=injections,
        adopted=adopted,
        declined=declined,
    )


def decide_from(found: Scan, verification: str | None, enabled: bool) -> GateDecision:
    command = found.adopted or verification
    if not enabled:
        return GateDecision("allow", "ok", command=command)
    if not found.pending:
        return GateDecision("allow", "ok", command=command)
    if command is None:
        if found.declined:
            return GateDecision("allow", "declined")
        if found.injections >= MAX_INJECTIONS:
            return GateDecision("give_up", "gave_up", injections=found.injections)
        return GateDecision("ask", "no_command", injections=found.injections)
    if found.injections >= MAX_INJECTIONS:
        return GateDecision("give_up", "gave_up", command=command, injections=found.injections)
    return GateDecision("block", "unverified_changes", command=command, injections=found.injections)


def decide(messages: Sequence[Any], verification: str | None, enabled: bool) -> GateDecision:
    return decide_from(scan(messages, verification), verification, enabled)


def instruction(decision: GateDecision) -> str:
    if decision.action == "ask":
        return (
            "[harness] Files changed but no verification command is configured. "
            "Call ask_user_question once with header 'Verification' and two to four "
            "candidate commands (for example 'pytest -q' and 'npm test') so the person "
            "can choose, then run the chosen command."
        )
    return (
        f"[harness] Files changed and no check has passed since. "
        f"Run `{decision.command}` and fix any failure before you finish. "
        "Approved changes stay on disk; this message is not a new task."
    )


class VerifyGateMiddleware(AgentMiddleware[AgentState[Any], Any, Any]):
    def __init__(
        self,
        bus: EventBus,
        verification: str | None,
        *,
        enabled: bool = True,
        adopt: Callable[[str], None] | None = None,
    ) -> None:
        self.bus = bus
        self.verification = verification
        self.enabled = enabled
        self.adopt = adopt
        self.adopted: str | None = None

    @hook_config(can_jump_to=["model"])
    async def aafter_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None
        found = scan(messages, self.verification)
        decision = decide_from(found, self.verification, self.enabled)
        # Adopt as soon as the person answers, so the next command is already "the check".
        self.remember(decision)
        last = messages[-1]
        if not isinstance(last, AIMessage) or last.tool_calls:
            return None
        if decision.action == "allow":
            if decision.reason == "declined":
                await self.announce_declined()
            return None
        if decision.action == "give_up":
            await self.announce_give_up()
            return None
        await self.bus.emit(
            "verify.required",
            reason="unverified_changes" if decision.action == "block" else "no_command",
            command=decision.command,
            injections=decision.injections + 1,
            blocked=True,
        )
        return {
            "messages": [
                HumanMessage(
                    content=instruction(decision),
                    name="harness",
                    additional_kwargs={"harness": INJECTED},
                )
            ],
            "jump_to": "model",
        }

    def remember(self, decision: GateDecision) -> None:
        if decision.command and decision.command != self.verification:
            self.verification = decision.command
            if self.adopt is not None and decision.command != self.adopted:
                self.adopted = decision.command
                self.adopt(decision.command)

    async def announce_give_up(self) -> None:
        # One notice per run: the gate stops blocking, it does not loop on this.
        if any(
            event.type == "budget.exhausted" and event.kind == "verify"
            for event in self.bus.history
        ):
            return
        await self.bus.emit("budget.exhausted", kind="verify", limit=MAX_INJECTIONS)

    async def announce_declined(self) -> None:
        if any(
            event.type == "verify.required" and event.reason == "declined"
            for event in self.bus.history
        ):
            return
        await self.bus.emit(
            "verify.required", reason="declined", command=None, injections=0, blocked=False
        )
