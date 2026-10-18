"""Consume deepagents streams into durable, replayable harness events."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.events import Event, RunRequest
from agent.factory import build_agent
from providers.demo import DemoModel
from providers.openai_compat import configured_model
from store.eventlog import EventBus
from store.secrets import Redactor, StreamRedactor
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
    ) -> None:
        self.runs: dict[str, Run] = {}
        self.redactor = Redactor(secrets_to_redact)
        self.demo_delay = demo_delay

    def contains(self, run_id: str) -> bool:
        return run_id in self.runs

    async def start(self, request: RunRequest) -> str:
        root = workspace_root(request.workspace)
        model = DemoModel(delay=self.demo_delay) if request.model == "demo" else configured_model()
        run_id = uuid4().hex
        path = storage_path(root, f"runs/{run_id}/events.jsonl")
        checkpoint = storage_path(root, "checkpoints.sqlite")
        bus = EventBus(path, run_id, self.redactor)
        safe_task = self.redactor.text(request.task)
        await bus.emit("run.started", task=safe_task, model=request.model)

        async def execute() -> None:
            buffers: dict[str, StreamRedactor] = {}
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
                            if isinstance(chunk, AIMessageChunk) and isinstance(chunk.content, str):
                                identifier = chunk.id or "assistant"
                                buffer = buffers.setdefault(
                                    identifier, StreamRedactor(self.redactor)
                                )
                                text = buffer.push(chunk.content)
                                if text:
                                    await bus.emit(
                                        "message.delta", message_id=identifier, text=text
                                    )
                        elif mode == "updates":
                            for update in payload.values():
                                if not isinstance(update, dict):
                                    continue
                                for message in update.get("messages", []):
                                    if isinstance(message, AIMessage):
                                        identifier = message.id or "assistant"
                                        if identifier in buffers:
                                            tail = buffers[identifier].push("", final=True)
                                            if tail:
                                                await bus.emit(
                                                    "message.delta",
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
                                    elif isinstance(message, ToolMessage):
                                        await bus.emit(
                                            "tool.result",
                                            call_id=message.tool_call_id,
                                            text=str(message.content),
                                        )
                await bus.emit("run.finished", status="completed")
            except asyncio.CancelledError:
                await bus.emit("run.finished", status="stopped")
            except Exception:
                # Provider errors may contain request headers/keys. Never serialize exceptions.
                await bus.emit(
                    "run.error", message="Run failed. Check the workspace and model configuration."
                )
                await bus.emit("run.finished", status="error")

        self.runs[run_id] = Run(bus, asyncio.create_task(execute()))
        return run_id

    async def stop(self, run_id: str) -> None:
        run = self.runs[run_id]
        if not run.task.done():
            run.task.cancel()
            try:
                await run.task
            except asyncio.CancelledError:
                # Cancellation before execute() starts has no coroutine handler yet.
                pass
            if not run.bus.finished:
                await run.bus.emit("run.finished", status="stopped")

    def events(self, run_id: str, after: int) -> AsyncIterator[Event]:
        return self.runs[run_id].bus.events(after)

    async def close(self) -> None:
        for run_id in self.runs:
            await self.stop(run_id)
