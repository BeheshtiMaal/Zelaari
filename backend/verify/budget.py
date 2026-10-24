"""Run budgets: model turns, wall clock and fix attempts, counted from real history.

Nothing here trusts the model's own accounting. A step is a model turn that asked for
tools, a fix attempt is a failed run of the verification command since the last pass,
and the clock starts at the run's first event — so a restored run resumes with the same
numbers instead of a fresh allowance.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from planning.gate import record_from_state
from planning.progress import active_step
from questions.exhausted import exhausted_question
from questions.types import QuestionInput
from store.eventlog import EventBus
from verify.gate import VerifyGateMiddleware
from verify.results import matches_verification, run_outcome
from verify.settings import VerifySettings

MARK = "budget"
MAX_OUTPUT = 4000
MAX_STEP = 160
Clock = Literal["steps", "time"]
Choice = Literal["ask", "retry", "change", "stop"]


@dataclass(frozen=True)
class Usage:
    steps: int
    fix_attempts: int
    elapsed_ms: int
    max_steps: int
    max_seconds: int
    max_fix_attempts: int


@dataclass(frozen=True)
class Reflection:
    """The state of the fix loop, read from the messages rather than remembered."""

    attempts: int = 0
    option: str | None = None
    hint: str | None = None
    asked: bool = False
    handled: bool = False
    stopped: bool = False


def command_of(args: Any) -> str | None:
    if isinstance(args, dict):
        value = args.get("command")
        if isinstance(value, str) and value.strip():
            return value
    return None


def steps_used(messages: Sequence[Any]) -> int:
    """One step is one model turn that emitted tool calls."""
    return sum(1 for message in messages if isinstance(message, AIMessage) and message.tool_calls)


def exhausted_answer(message: ToolMessage) -> tuple[bool, str | None, str | None]:
    """Read an exhausted card's answer: the chosen option and any guidance."""
    try:
        answer = json.loads(str(message.content))
    except ValueError:
        return False, None, None
    if not isinstance(answer, dict):
        return False, None, None
    if answer.get("status") == "declined":
        return True, "declined", None
    selections = answer.get("answers")
    if not isinstance(selections, list):
        return False, None, None
    for selection in selections:
        if not isinstance(selection, dict):
            continue
        hint = selection.get("hint")
        guidance = hint if isinstance(hint, str) and hint.strip() else None
        other = selection.get("other")
        if isinstance(other, str) and other.strip():
            # Typing your own guidance is a retry with that guidance.
            return True, "retry", other.strip()
        chosen = selection.get("option_ids")
        if isinstance(chosen, list) and chosen:
            return True, str(chosen[0]), guidance
    return False, None, None


def reflect(messages: Sequence[Any], verification: str | None) -> Reflection:
    calls: dict[str, dict[str, Any]] = {}
    attempts = 0
    option: str | None = None
    hint: str | None = None
    asked = False
    handled = False
    stopped = False
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                if tool_call.get("id"):
                    calls[str(tool_call["id"])] = dict(tool_call)
            continue
        if isinstance(message, HumanMessage):
            if message.additional_kwargs.get("harness") == MARK:
                if message.additional_kwargs.get("kind") == "ask":
                    asked = True
                else:
                    handled = True
            continue
        if not isinstance(message, ToolMessage):
            continue
        call = calls.get(str(message.tool_call_id), {})
        name = call.get("name") or message.name
        if name == "run_command":
            command = command_of(call.get("args"))
            if not verification or not command or not matches_verification(command, verification):
                continue
            outcome = run_outcome(str(message.content))
            if outcome is None:
                continue
            if outcome.exit_code == 0:
                attempts = 0
            else:
                attempts += 1
                asked = False
                handled = False
                option, hint = None, None
            continue
        if name == "ask_user_question" and str(
            (call.get("args") or {}).get("presentation", "")
        ) == "exhausted":
            answered, chosen, guidance = exhausted_answer(message)
            if not answered:
                continue
            attempts = 0
            asked = False
            handled = False
            option, hint = chosen, guidance
            stopped = stopped or chosen in {"stop", "declined"}
    return Reflection(
        attempts=attempts,
        option=option,
        hint=hint,
        asked=asked,
        handled=handled,
        stopped=stopped,
    )


def usage_of(
    messages: Sequence[Any], verification: str | None, settings: VerifySettings, elapsed_ms: int
) -> Usage:
    return Usage(
        steps=steps_used(messages),
        fix_attempts=reflect(messages, verification).attempts,
        elapsed_ms=max(0, elapsed_ms),
        max_steps=settings.max_steps,
        max_seconds=settings.max_minutes * 60,
        max_fix_attempts=settings.fix_attempts,
    )


def reached(usage: Usage) -> Clock | None:
    """Steps come first: a run that is out of turns cannot spend more time either."""
    if usage.steps >= usage.max_steps:
        return "steps"
    if usage.elapsed_ms >= usage.max_seconds * 1000:
        return "time"
    return None


def limit_of(usage: Usage, kind: Clock) -> int:
    return usage.max_steps if kind == "steps" else usage.max_seconds


def choice_of(found: Reflection, max_attempts: int) -> Choice | None:
    if found.option and not found.handled:
        if found.option in {"stop", "declined"}:
            return "stop"
        if found.option == "change":
            return "change"
        return "retry"
    if max_attempts >= 1 and found.attempts >= max_attempts and not found.asked:
        return "ask"
    return None


def payload(attempts: int, step: str, check: str, output: str) -> QuestionInput:
    return exhausted_question(attempts, step[:MAX_STEP], check, output[:MAX_OUTPUT])


def ask_instruction(question: QuestionInput) -> str:
    body = json.dumps(question.model_dump(mode="json"), ensure_ascii=False)
    return (
        "[harness] The check has failed too many times on this step. Ask the person once "
        f"with exactly these arguments to ask_user_question: {body} "
        "Change nothing until it is answered."
    )


def retry_instruction(hint: str | None) -> str:
    guidance = f"Their guidance: {hint}" if hint else "They gave no further guidance."
    return (
        f"[harness] The person asked for another attempt on this step. {guidance} "
        "Use it, then run the check again."
    )


def change_instruction() -> str:
    return (
        "[harness] The person asked for a different approach. Submit a revised plan with "
        "submit_plan for this step before any further change, then run the check."
    )


def stop_instruction() -> str:
    return (
        "[harness] The person chose to stop. Do not call tools. Report what changed and "
        "what still fails, then finish."
    )


class BudgetMiddleware(AgentMiddleware[AgentState[Any], Any, Any]):
    """Emits the counters, stops the run at a cap, and runs the fix loop.

    Injection happens in `abefore_model`, where the last message is a tool result or an
    instruction: a tool call the model just made is never skipped.
    """

    def __init__(
        self,
        bus: EventBus,
        settings: VerifySettings,
        verification: str | None,
        *,
        gate: VerifyGateMiddleware | None = None,
        stop: Callable[[], None] | None = None,
        wall: Callable[[], datetime] | None = None,
    ) -> None:
        self.bus = bus
        self.settings = settings
        self.verification = verification
        self.gate = gate
        self.stop = stop or (lambda: None)
        self.wall = wall or (lambda: datetime.now(UTC))

    def elapsed_ms(self) -> int:
        started = self.bus.history[0].ts if self.bus.history else self.wall()
        return max(0, int((self.wall() - started).total_seconds() * 1000))

    async def abefore_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None
        usage = usage_of(messages, self.verification, self.settings, self.elapsed_ms())
        await self.publish(usage)
        clock = reached(usage)
        if clock is not None and not self.announced(clock):
            await self.bus.emit("budget.exhausted", kind=clock, limit=limit_of(usage, clock))
            self.stop()
            return None
        found = reflect(messages, self.verification)
        if found.stopped and self.gate is not None:
            # The person stopped: the gate must not hold the report hostage.
            self.gate.enabled = False
        choice = choice_of(found, usage.max_fix_attempts)
        if choice is None:
            return None
        return {"messages": [self.instruction(choice, found, state)]}

    def announced(self, clock: Clock) -> bool:
        return any(
            event.type == "budget.exhausted" and event.kind == clock for event in self.bus.history
        )

    async def publish(self, usage: Usage) -> None:
        payload: dict[str, int] = {
            "steps": usage.steps,
            "max_steps": usage.max_steps,
            "fix_attempts": usage.fix_attempts,
            "max_fix_attempts": usage.max_fix_attempts,
            "elapsed_ms": usage.elapsed_ms,
            "max_seconds": usage.max_seconds,
        }
        for event in reversed(self.bus.history):
            if event.type == "budget.updated":
                if all(getattr(event, key) == value for key, value in payload.items()):
                    return
                break
        await self.bus.emit("budget.updated", **payload)

    def instruction(
        self, choice: Choice, found: Reflection, state: AgentState[Any]
    ) -> HumanMessage:
        if choice == "ask":
            step = self.current_step(state)
            check = self.verification or "the check"
            output = self.last_failure(state)
            content = ask_instruction(payload(found.attempts, step, check, output))
        elif choice == "retry":
            content = retry_instruction(found.hint)
        elif choice == "change":
            content = change_instruction()
        else:
            content = stop_instruction()
        return HumanMessage(
            content=content, name="harness", additional_kwargs={"harness": MARK, "kind": choice}
        )

    def current_step(self, state: AgentState[Any]) -> str:
        plan = record_from_state(dict(state))
        step = active_step(plan) if plan is not None else None
        return step.title if step is not None else "this step"

    def last_failure(self, state: AgentState[Any]) -> str:
        """The output of the last failed run of the verification command."""
        calls: dict[str, dict[str, Any]] = {}
        output = ""
        for message in state.get("messages", []):
            if isinstance(message, AIMessage):
                for tool_call in message.tool_calls:
                    if tool_call.get("id"):
                        calls[str(tool_call["id"])] = dict(tool_call)
                continue
            if not isinstance(message, ToolMessage):
                continue
            call = calls.get(str(message.tool_call_id), {})
            if (call.get("name") or message.name) != "run_command":
                continue
            command = command_of(call.get("args"))
            if not self.verification or not command:
                continue
            if not matches_verification(command, self.verification):
                continue
            outcome = run_outcome(str(message.content))
            if outcome is not None and outcome.exit_code != 0:
                output = outcome.output
        return output
