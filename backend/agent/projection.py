"""Project real graph updates into the single durable scoped event stream."""

import hashlib
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from agent.activity import identity
from agent.meter import TokenMeter, content_parts
from planning.gate import record_from_state
from planning.publication import publish_plan
from planning.types import ActivityScope
from store.delegates import DelegateResults
from store.eventlog import EventBus
from store.secrets import StreamRedactor


class ActivityProjection:
    def __init__(
        self,
        bus: EventBus,
        meter: TokenMeter,
        context_window: int | None,
        context_window_estimated: bool = False,
    ) -> None:
        self.bus = bus
        self.meter = meter
        self.window = context_window
        self.window_estimated = context_window_estimated
        self.scopes: dict[tuple[str, ...], ActivityScope] = {}
        self.buffers: dict[str, StreamRedactor] = {}
        self.streamed: set[str] = set()
        self.finished: set[str] = set()

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
                        )
                    elif isinstance(message.additional_kwargs.get("_harness_input_tokens"), int):
                        await self.bus.emit(
                            "context.updated",
                            scope=scope,
                            input_tokens=message.additional_kwargs["_harness_input_tokens"],
                            context_window=self.window,
                            context_window_estimated=self.window_estimated,
                            estimated=True,
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
