"""Consume deepagents streams into durable, replayable harness events."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.events import Event, RunRequest
from agent.factory import build_agent
from agent.meter import TokenMeter, content_parts
from providers.adapters import chat_model
from providers.base import TaskRecord
from providers.context import detect_context
from providers.demo import DemoModel
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor, StreamRedactor
from store.workspaces import add_task, select_workspace
from tools.jail import storage_path, workspace_root


@dataclass
class Run:
    bus: EventBus
    task: asyncio.Task[None]


class RunManager:
    def __init__(
        self,
        secrets_to_redact: list[str] | None = None,
        *,
        demo_delay: float = 0.012,
        catalog: Catalog | None = None,
    ) -> None:
        self.runs: dict[str, Run] = {}
        self.redactor = Redactor(secrets_to_redact)
        self.demo_delay = demo_delay
        self.catalog = catalog or Catalog(redactor=self.redactor)
        self.redactor = self.catalog.redactor

    def contains(self, run_id: str) -> bool:
        return run_id in self.runs

    async def start(self, request: RunRequest) -> str:
        root = workspace_root(request.workspace)
        record = self.catalog.require(request.model)
        model = (
            DemoModel(delay=self.demo_delay)
            if record.kind == "demo"
            else chat_model(record, self.catalog.keys[request.model])
        )
        run_id = uuid4().hex
        path = storage_path(root, f"runs/{run_id}/events.jsonl")
        checkpoint = storage_path(root, "checkpoints.sqlite")
        bus = EventBus(path, run_id, self.redactor)
        safe_task = self.redactor.text(request.task)
        await bus.emit("run.started", task=safe_task, model=request.model)
        select_workspace(self.catalog, str(root))
        task_record = TaskRecord(
            id=run_id,
            workspace=str(root),
            title=safe_task[:240],
            model=request.model,
            mode=request.mode,
        )
        add_task(self.catalog, task_record)

        async def execute() -> None:
            buffers: dict[str, StreamRedactor] = {}
            prompt = Path(__file__).with_name("genui_prompt.txt").read_text(encoding="utf-8")
            meter = TokenMeter(len(safe_task) + len(prompt))
            streamed: set[str] = set()
            try:
                async with AsyncSqliteSaver.from_conn_string(str(checkpoint)) as saver:
                    graph = build_agent(root, model, saver, self.redactor)
                    stream = graph.astream(
                        {"messages": [{"role": "user", "content": safe_task}]},
                        {"configurable": {"thread_id": run_id}, "recursion_limit": 24},
                        stream_mode=["messages", "updates"],
                        subgraphs=True,
                    )
                    async for namespace, mode, payload in cast(
                        AsyncIterator[tuple[tuple[str, ...], str, Any]],
                        stream,
                    ):
                        if namespace:
                            continue
                        if mode == "messages":
                            chunk, _metadata = payload
                            if isinstance(chunk, AIMessageChunk):
                                identifier = chunk.id or "assistant"
                                for kind, value in zip(
                                    ("message.delta", "reasoning.delta"),
                                    content_parts(chunk),
                                    strict=True,
                                ):
                                    buffer_id = identifier + kind
                                    if value:
                                        streamed.add(buffer_id)
                                    buffer = buffers.setdefault(
                                        buffer_id, StreamRedactor(self.redactor)
                                    )
                                    text = buffer.push(value)
                                    if text:
                                        await bus.emit(kind, message_id=identifier, text=text)
                        elif mode == "updates":
                            for update in payload.values():
                                if not isinstance(update, dict):
                                    continue
                                for message in update.get("messages", []):
                                    if isinstance(message, AIMessage):
                                        identifier = message.id or "assistant"
                                        for kind, value in zip(
                                            ("message.delta", "reasoning.delta"),
                                            content_parts(message),
                                            strict=True,
                                        ):
                                            buffer_id = identifier + kind
                                            buffer = buffers.setdefault(
                                                buffer_id, StreamRedactor(self.redactor)
                                            )
                                            tail = buffer.push(
                                                "" if buffer_id in streamed else value, final=True
                                            )
                                            if tail:
                                                await bus.emit(
                                                    kind,
                                                    message_id=identifier,
                                                    text=tail,
                                                )
                                        for call in message.tool_calls:
                                            await bus.emit(
                                                "tool.call",
                                                call_id=call["id"],
                                                name=call["name"],
                                                args=call["args"],
                                            )
                                        if meter.turn(message, identifier):
                                            await bus.emit(
                                                "usage.updated",
                                                input_tokens=meter.input_tokens,
                                                output_tokens=meter.output_tokens,
                                                estimated=meter.estimated,
                                            )
                                    elif isinstance(message, ToolMessage):
                                        meter.input_characters += len(str(message.content))
                                        await bus.emit(
                                            "tool.result",
                                            call_id=message.tool_call_id,
                                            text=str(message.content),
                                        )
                await bus.emit("run.finished", status="completed")
            except asyncio.CancelledError:
                await bus.emit("run.finished", status="stopped")
            except Exception as error:
                if record.kind != "demo" and record.context.source == "fallback":
                    context = detect_context(record.model, error=str(error))
                    current = self.catalog.data.models.get(record.id)
                    if (
                        context.source == "error"
                        and current
                        and current.model == record.model
                        and current.base_url == record.base_url
                        and current.context.source == "fallback"
                    ):
                        current.context = context
                        self.catalog.persist()
                # Provider errors may contain request headers/keys. Never serialize exceptions.
                await bus.emit(
                    "run.error", message="Run failed. Check the workspace and model configuration."
                )
                await bus.emit("run.finished", status="error")
            finally:
                final = bus.history[-1]
                if final.type == "run.finished":
                    task_record.status = final.status
                self.catalog.persist()

        self.runs[run_id] = Run(bus, asyncio.create_task(execute()))
        return run_id

    async def stop(self, run_id: str) -> None:
        run = self.runs[run_id]
        if not run.bus.finished:
            run.task.cancel()
            # Report cancellation before SQLite/HTTP cleanup. Terminal buses reject
            # late events, so cleanup cannot append results or another finish.
            await run.bus.emit("run.finished", status="stopped")

    def events(self, run_id: str, after: int) -> AsyncIterator[Event]:
        return self.runs[run_id].bus.events(after)

    async def close(self) -> None:
        for run_id in self.runs:
            await self.stop(run_id)
        await asyncio.gather(*(run.task for run in self.runs.values()), return_exceptions=True)
