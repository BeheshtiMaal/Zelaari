"""Consume deepagents streams into durable, replayable harness events."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.events import Event, RunRequest
from agent.factory import build_agent
from agent.meter import TokenMeter, content_parts
from permissions.middleware import PermissionMiddleware
from permissions.rules import RulesEngine
from permissions.types import (
    ApprovalAnswer,
    ApprovalDecision,
    ApprovalRequest,
    UnknownApproval,
)
from providers.adapters import chat_model
from providers.base import TaskRecord
from providers.context import detect_context
from providers.demo import DemoModel
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor, StreamRedactor
from store.workspaces import add_task, select_workspace
from tools.command import CommandRunner, build_run_command
from tools.git import add_worktree, build_git_switch
from tools.jail import storage_path, workspace_root
from tools.snapshot import SnapshotStore


class WorktreeApprovalRequired(Exception):
    """The run asked for a worktree without the person confirming it first."""

    def __init__(self, approval: ApprovalRequest) -> None:
        super().__init__("Worktree creation needs approval")
        self.approval = approval


@dataclass
class Run:
    bus: EventBus
    task: asyncio.Task[None]
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    pending: ApprovalRequest | None = None
    answer: ApprovalAnswer | None = None


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

    def pending_paths(self) -> set[str]:
        """Paths a paused run is waiting on, so the file viewer can badge them."""
        return {
            run.pending.path.replace("\\", "/")
            for run in self.runs.values()
            if run.pending is not None and run.pending.path
        }

    async def start(self, request: RunRequest) -> str:
        workspace = workspace_root(request.workspace)
        record = self.catalog.require(request.model)
        model = (
            DemoModel(delay=self.demo_delay)
            if record.kind == "demo"
            else chat_model(record, self.catalog.keys[request.model])
        )
        run_id = uuid4().hex
        # History and checkpoints stay in the selected workspace even when the agent
        # works in a worktree, so one task list and one replay log cover both.
        root = workspace
        worktree: Path | None = None
        if request.worktree:
            if not request.worktree_approved:
                raise WorktreeApprovalRequired(
                    ApprovalRequest(
                        approval_id=f"worktree:{run_id}",
                        run_id=run_id,
                        kind="command",
                        tool="worktree_create",
                        path=f".harness/worktrees/{run_id}",
                        reason="creating a worktree writes engine storage and adds a branch",
                    )
                )
            worktree = add_worktree(workspace, run_id)
            root = worktree
        path = storage_path(workspace, f"runs/{run_id}/events.jsonl")
        checkpoint = storage_path(workspace, "checkpoints.sqlite")
        bus = EventBus(path, run_id, self.redactor)
        safe_task = self.redactor.text(request.task)
        await bus.emit("run.started", task=safe_task, model=request.model)
        select_workspace(self.catalog, str(workspace))
        task_record = TaskRecord(
            id=run_id,
            workspace=str(workspace),
            title=safe_task[:240],
            model=request.model,
            mode=request.mode,
            worktree=str(worktree) if worktree else None,
        )
        add_task(self.catalog, task_record)

        async def execute() -> None:
            run = self.runs[run_id]
            buffers: dict[str, StreamRedactor] = {}
            prompt = Path(__file__).with_name("genui_prompt.txt").read_text(encoding="utf-8")
            meter = TokenMeter(len(safe_task) + len(prompt))
            streamed: set[str] = set()
            try:
                async with AsyncSqliteSaver.from_conn_string(str(checkpoint)) as saver:
                    rules = RulesEngine.load(root, request.mode)
                    runner = CommandRunner(root, self.redactor, secrets=self.redactor.values)
                    graph = build_agent(
                        root,
                        model,
                        saver,
                        self.redactor,
                        permissions=PermissionMiddleware(rules, run_id=run_id),
                        snapshots=SnapshotStore(root, run_id=run_id),
                        extra_tools=[
                            build_run_command(runner),
                            build_git_switch(root),
                        ],
                    )
                    config: RunnableConfig = {
                        "configurable": {"thread_id": run_id},
                        "recursion_limit": 24,
                    }
                    payload: Any = {"messages": [{"role": "user", "content": safe_task}]}
                    while True:
                        async for namespace, mode, update in cast(
                            AsyncIterator[tuple[tuple[str, ...], str, Any]],
                            graph.astream(
                                payload,
                                config,
                                stream_mode=["messages", "updates"],
                                subgraphs=True,
                            ),
                        ):
                            if namespace:
                                continue
                            if mode == "messages":
                                chunk, _metadata = update
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
                                if "__interrupt__" in update:
                                    await self._announce(run, update["__interrupt__"])
                                    continue
                                for change in update.values():
                                    if not isinstance(change, dict):
                                        continue
                                    for message in change.get("messages", []):
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
                                                    "" if buffer_id in streamed else value,
                                                    final=True,
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

                        # An interrupt ends the stream but not the run: the graph still
                        # has a node to re-execute once the decision arrives.
                        snapshot = await graph.aget_state(config)
                        if not snapshot.next:
                            break
                        answer = await self._answer(run)
                        if answer is None:
                            break
                        payload = Command(resume=answer.model_dump(mode="json"))
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

    # -- approvals ---------------------------------------------------------
    async def _announce(self, run: Run, interrupts: Any) -> None:
        """Publish the pause. The middleware never emits, so a replayed node cannot duplicate it."""
        for item in interrupts:
            value = getattr(item, "value", None)
            if not isinstance(value, dict):
                continue
            request = ApprovalRequest.model_validate(value)
            run.pending = request
            await run.bus.emit("approval.requested", approval=request)

    async def _answer(self, run: Run) -> ApprovalAnswer | None:
        """Block until the person decides. Returns None if the run was stopped first."""
        await run.ready.wait()
        answer, run.answer = run.answer, None
        run.ready.clear()
        run.pending = None
        return answer

    async def resolve(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> None:
        run = self.runs[run_id]
        pending = run.pending
        if pending is None or pending.approval_id != approval_id or run.answer is not None:
            raise UnknownApproval(approval_id)
        run.answer = ApprovalAnswer(
            approval_id=approval_id,
            decision=decision.decision,
            reason=decision.reason,
        )
        run.pending = None
        await run.bus.emit(
            "approval.resolved",
            approval_id=approval_id,
            decision=decision.decision,
            reason=decision.reason,
        )
        run.ready.set()

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
