"""Project real graph updates into the single durable scoped event stream."""

import hashlib
import json
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from agent.activity import identity
from agent.meter import TokenMeter, content_parts
from planning.gate import record_from_state
from planning.publication import publish_plan
from planning.types import ActivityScope
from skills.registry import Registry
from store.delegates import DelegateResults
from store.eventlog import EventBus
from store.secrets import StreamRedactor
from verify.context import ContextBreakdown, Window
from verify.results import matches_verification, parse_test_output


class ActivityProjection:
    def __init__(
        self,
        bus: EventBus,
        meter: TokenMeter,
        context_window: int | None,
        context_window_estimated: bool = False,
        verification: str | None = None,
        prompt: Window | None = None,
        skills: Registry | None = None,
    ) -> None:
        self.bus = bus
        self.meter = meter
        self.window = context_window
        self.window_estimated = context_window_estimated
        self.verification = verification
        self.prompt = prompt
        self.scopes: dict[tuple[str, ...], ActivityScope] = {}
        self.buffers: dict[str, StreamRedactor] = {}
        self.streamed: set[str] = set()
        self.finished: set[str] = set()
        self.commands: dict[str, str] = {}
        self.programs: dict[str, str] = {}
        self.tested: set[str] = set()
        self.skills = skills
        self.loaded: set[str] = set()

    async def content(
        self, namespace: tuple[str, ...], message: AIMessage | AIMessageChunk, final: bool
    ) -> None:
        scope = self.scopes.get(namespace)
        if scope is None:
            return
        identifier = scope.scope_id
        for kind, value in zip(
            ("message.delta", "reasoning.delta"), content_parts(message), strict=True
        ):
            key = scope.scope_id + identifier + kind
            buffer = self.buffers.setdefault(key, StreamRedactor(self.bus.redactor))
            if final:
                text = buffer.push("" if key in self.streamed else value, final=True)
            else:
                if value:
                    self.streamed.add(key)
                text = buffer.push(value)
            if text:
                await self.bus.emit(kind, scope=scope, message_id=identifier, text=text)

    def measured(self) -> ContextBreakdown | None:
        """The split of the prompt the model just received, counted the summarizer's way."""
        return self.prompt.breakdown() if self.prompt is not None else None

    async def test_result(self, message: ToolMessage, scope: ActivityScope) -> None:
        """Emit `test.result` only for the run's verification command, from real output."""
        if not self.verification or message.tool_call_id in self.tested:
            return
        command = self.commands.get(str(message.tool_call_id))
        if command is None or not matches_verification(command, self.verification):
            return
        try:
            payload = json.loads(str(message.content))
        except ValueError:
            return
        if not isinstance(payload, dict):
            return
        self.tested.add(message.tool_call_id)
        exit_code = payload.get("exit_code")
        duration = payload.get("duration_ms")
        outcome = parse_test_output(
            command=command,
            exit_code=exit_code if isinstance(exit_code, int) else None,
            timed_out=payload.get("timed_out") is True,
            duration_ms=duration if isinstance(duration, int) else 0,
            output=str(payload.get("output", "")),
            redact=self.bus.redactor.text,
        )
        await self.bus.emit(
            "test.result",
            scope=scope,
            call_id=message.tool_call_id,
            command=command,
            **outcome.model_dump(),
        )

    async def render_ui(self, message: ToolMessage, scope: ActivityScope) -> None:
        """Emit `ui.render` for one attempt, from the program the model actually sent.

        A successful render is evidence: the timeline draws the program. A failed one keeps
        the program and the one-line reason, so a silent fallback can never hide it.
        """
        program = self.programs.pop(str(message.tool_call_id), None)
        if program is None:
            return
        payload: dict[str, Any] = {}
        try:
            parsed = json.loads(str(message.content))
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            payload = parsed
        if not isinstance(payload.get("ok"), bool):
            # The tool contract rejected the call before it ran; that is still a failure.
            payload = {"ok": False, "error": str(message.content)[:200]}
        components = payload.get("components")
        statements = payload.get("statements")
        error = payload.get("error")
        await self.bus.emit(
            "ui.render",
            scope=scope,
            call_id=message.tool_call_id,
            ok=payload["ok"] is True,
            text=program,
            components=(
                [str(item) for item in components][:32] if isinstance(components, list) else []
            ),
            statements=statements if isinstance(statements, int) and statements >= 0 else 0,
            error=str(error)[:200] if isinstance(error, str) else None,
        )

    async def skill_loaded(self, name: object) -> None:
        """One event per skill body actually handed to the model."""
        if self.skills is None or not isinstance(name, str) or name in self.loaded:
            return
        record = self.skills.find(name)
        if record is None:
            return
        self.loaded.add(name)
        await self.bus.emit(
            "skill.loaded",
            name=record.name,
            source=record.source,
            command=record.command,
            tokens=record.tokens,
        )

    async def update(self, namespace: tuple[str, ...], update: dict[str, Any]) -> None:
        for change in update.values():
            if not isinstance(change, dict):
                continue
            if not namespace:
                await publish_plan(self.bus, record_from_state(change))
            scope_value = change.get("child_activity_scope") or change.get("activity_scope")
            if scope_value:
                previous = self.scopes.get(namespace)
                if previous and previous.scope_id not in self.finished:
                    await self.bus.emit("activity.finished", scope=previous, status="completed")
                    self.finished.add(previous.scope_id)
                new_scope = ActivityScope.model_validate(scope_value)
                self.scopes[namespace] = new_scope
                await self.bus.emit("activity.started", scope=new_scope)
            scope = self.scopes.get(namespace)
            if scope is None:
                continue
            summary = change.get("_summarization_event")
            summary_data = summary if isinstance(summary, dict) else {}
            notice = change.get("summary_notice")
            if isinstance(summary, dict) or isinstance(notice, dict):
                operation = (
                    str(notice["operation_id"])
                    if isinstance(notice, dict)
                    else hashlib.sha256((str(namespace) + str(summary)).encode()).hexdigest()
                )
                if not any(
                    e.type == "context.summarized" and e.operation_id == operation
                    for e in self.bus.history
                ):
                    usage = (
                        notice.get("usage")
                        if isinstance(notice, dict)
                        else getattr(
                            summary_data.get("summary_message"), "additional_kwargs", {}
                        ).get("_harness_usage")
                    )
                    if isinstance(usage, dict):
                        self.meter.input_tokens += int(usage["input_tokens"])
                        self.meter.output_tokens += int(usage["output_tokens"])
                        self.meter.estimated |= bool(usage["estimated"])
                        await self.bus.emit(
                            "usage.updated",
                            input_tokens=self.meter.input_tokens,
                            output_tokens=self.meter.output_tokens,
                            estimated=self.meter.estimated,
                        )
                    count = (
                        notice.get("affected_messages")
                        if isinstance(notice, dict)
                        else summary_data.get("cutoff_index")
                    )
                    await self.bus.emit(
                        "context.summarized",
                        scope=scope,
                        operation_id=operation,
                        affected_messages=count if isinstance(count, int) and count > 0 else None,
                    )
            for message in change.get("messages", []):
                if isinstance(message, AIMessage):
                    await self.content(namespace, message, True)
                    for call in message.tool_calls:
                        command = call["args"].get("command")
                        if (
                            call["name"] == "run_command"
                            and call["id"]
                            and isinstance(command, str)
                        ):
                            self.commands[call["id"]] = command
                        if (
                            call["name"] == "render_ui"
                            and call["id"]
                            and isinstance(call["args"].get("ui"), str)
                        ):
                            self.programs[call["id"]] = str(call["args"]["ui"])
                        if call["name"] == "load_skill":
                            await self.skill_loaded(call["args"].get("name"))
                        await self.bus.emit(
                            "tool.call",
                            scope=scope,
                            call_id=call["id"],
                            name=call["name"],
                            args=call["args"],
                        )
                    if message.usage_metadata:
                        await self.bus.emit(
                            "context.updated",
                            scope=scope,
                            input_tokens=message.usage_metadata["input_tokens"],
                            context_window=self.window,
                            context_window_estimated=self.window_estimated,
                            estimated=False,
                            breakdown=self.measured(),
                        )
                    elif isinstance(message.additional_kwargs.get("_harness_input_tokens"), int):
                        await self.bus.emit(
                            "context.updated",
                            scope=scope,
                            input_tokens=message.additional_kwargs["_harness_input_tokens"],
                            context_window=self.window,
                            context_window_estimated=self.window_estimated,
                            estimated=True,
                            breakdown=self.measured(),
                        )
                    if self.meter.turn(message, scope.scope_id + (message.id or "assistant")):
                        await self.bus.emit(
                            "usage.updated",
                            input_tokens=self.meter.input_tokens,
                            output_tokens=self.meter.output_tokens,
                            estimated=self.meter.estimated,
                        )
                    if not message.tool_calls and scope.scope_id not in self.finished:
                        await self.bus.emit("activity.finished", scope=scope, status="completed")
                        self.finished.add(scope.scope_id)
                elif isinstance(message, ToolMessage):
                    self.meter.input_characters += len(str(message.content))
                    await self.bus.emit(
                        "tool.result",
                        scope=scope,
                        call_id=message.tool_call_id,
                        text=str(message.content),
                    )
                    await self.test_result(message, scope)
                    await self.render_ui(message, scope)
                    if not namespace:
                        records = DelegateResults(
                            self.bus.path.with_name("delegates.json"), self.bus.redactor
                        )
                        invocation = identity(self.bus.run_id + message.tool_call_id)
                        result = records.records.get(invocation)
                        if result and not any(
                            event.type == "subagent.finished"
                            and event.scope.scope_id == result.scope.scope_id
                            and event.status == "completed"
                            for event in self.bus.history
                        ):
                            await self.bus.emit(
                                "subagent.finished",
                                scope=result.scope,
                                status="completed",
                                result=result.text,
                            )
