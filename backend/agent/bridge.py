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
from permissions.review import prepare_review
from permissions.rules import RulesEngine
from permissions.types import (
    ApprovalAnswer,
    ApprovalBatch,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    Rule,
    UnknownApproval,
)
from providers.adapters import chat_model
from providers.base import TaskRecord
from providers.context import detect_context
from providers.demo import DemoModel
from store.actions import ActionApprovals
from store.approvals import ApprovalLedger
from store.catalog import Catalog
from store.eventlog import EventBus
from store.secrets import Redactor, StreamRedactor
from store.workspaces import add_task, select_workspace
from tools.command import CommandRunner, build_run_command
from tools.git import add_worktree, build_git_switch, repository
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
    ledger: ApprovalLedger | None = None
    barrier: list[str] = field(default_factory=list)
    interrupt_id: str = ""
    preserving: bool = False


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
        self.actions = ActionApprovals(self.catalog)

    def contains(self, run_id: str) -> bool:
        return run_id in self.runs or any(
            record.request.run_id == run_id for record in self.actions.records()
        )

    def pending_paths(self) -> set[str]:
        """Paths a paused run is waiting on, so the file viewer can badge them."""
        paths = {
            run.pending.path.replace("\\", "/")
            for run in self.runs.values()
            if run.pending is not None and run.pending.path
        }
        for run in self.runs.values():
            if run.ledger:
                paths.update(
                    record.request.path.replace("\\", "/")
                    for record in run.ledger.records.values()
                    if record.status == "pending" and record.request.path
                )
        return paths

    async def start(
        self, request: RunRequest, *, restore_id: str | None = None, worktree_consent: bool = False
    ) -> str:
        workspace = workspace_root(request.workspace)
        record = self.catalog.require(request.model)
        model = (
            DemoModel(delay=self.demo_delay)
            if record.kind == "demo"
            else chat_model(record, self.catalog.keys[request.model])
        )
        run_id = restore_id or uuid4().hex
        # History and checkpoints stay in the selected workspace even when the agent
        # works in a worktree, so one task list and one replay log cover both.
        root = workspace
        worktree: Path | None = None
        if request.worktree and not restore_id:
            if not repository(workspace):
                raise ValueError("Worktrees require a Git repository")
            outcome = RulesEngine.load(workspace, request.mode).decide("worktree_create")
            if outcome.action == "deny":
                raise ValueError("Current permissions deny worktree creation")
            if not worktree_consent:
                raise WorktreeApprovalRequired(
                    self.actions.propose(
                        workspace,
                        ApprovalRequest(
                            approval_id=f"worktree:{run_id}",
                            run_id=run_id,
                            kind="command",
                            tool="worktree_create",
                            path=f".harness/worktrees/{run_id}",
                            reason="creating a worktree writes engine storage and adds a branch",
                            workspace=str(workspace),
                            args=request.model_dump(mode="json"),
                            source_title=self.redactor.text(request.task)[:240],
                        ),
                    ).request
                )
            worktree = add_worktree(workspace, run_id)
            root = worktree
        path = storage_path(workspace, f"runs/{run_id}/events.jsonl")
        checkpoint = storage_path(workspace, "checkpoints.sqlite")
        bus = EventBus(path, run_id, self.redactor)
        ledger = ApprovalLedger(storage_path(workspace, f"runs/{run_id}/approvals.json"))
        safe_task = self.redactor.text(request.task)
        if not restore_id:
            from tools.atomic import atomic_write

            atomic_write(
                storage_path(workspace, f"runs/{run_id}/request.json"),
                request.model_copy(update={"task": safe_task}).model_dump_json(),
            )
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
        if not restore_id:
            add_task(self.catalog, task_record)
        else:
            task_record = next(
                item for item in self.catalog.data.workspaces.tasks if item.id == run_id
            )
            if task_record.worktree:
                root = workspace_root(task_record.worktree)

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
                        permissions=PermissionMiddleware(
                            rules, run_id=run_id, redactor=self.redactor
                        ),
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
                    if restore_id:
                        snapshot = await graph.aget_state(config)
                        if snapshot.interrupts:
                            await self._announce(run, snapshot.interrupts)
                            payload = Command(resume=await self._resume(run))
                        else:
                            payload = None
                    while True:
                        async for namespace, mode, update in cast(
                            AsyncIterator[tuple[tuple[str, ...], str, Any]],
                            graph.astream(
                                payload,
                                config,
                                stream_mode=["messages", "updates"],
                                subgraphs=True,
                                durability="sync",
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
                        await self._announce(run, snapshot.interrupts)
                        payload = Command(resume=await self._resume(run))
                await bus.emit("run.finished", status="completed")
            except asyncio.CancelledError:
                if not run.preserving:
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
                    task_record.waiting_on = []
                self.catalog.persist()

        self.runs[run_id] = Run(bus, asyncio.create_task(execute()), ledger=ledger)
        return run_id

    async def recover(self) -> None:
        for item in self.catalog.data.workspaces.tasks:
            if item.id in self.runs:
                continue
            try:
                path = storage_path(workspace_root(item.workspace), f"runs/{item.id}/request.json")
                if not path.exists():
                    continue
                request = RunRequest.model_validate_json(path.read_bytes())
                bus = EventBus(path.with_name("events.jsonl"), item.id, self.redactor)
                if bus.finished:
                    continue
                await self.start(request, restore_id=item.id)
            except (OSError, ValueError):
                # Keep durable records available while credentials/workspace are unavailable.
                continue

    def approvals(self, status: str | None = None) -> list[ApprovalRecord]:
        result: list[ApprovalRecord] = [
            record for record in self.actions.records() if status is None or record.status == status
        ]
        for task in self.catalog.data.workspaces.tasks:
            try:
                ledger = ApprovalLedger(
                    storage_path(workspace_root(task.workspace), f"runs/{task.id}/approvals.json")
                )
                result.extend(
                    record
                    for record in ledger.records.values()
                    if status is None or record.status == status
                )
            except (OSError, ValueError):
                continue
        return result

    # -- approvals ---------------------------------------------------------
    async def _announce(self, run: Run, interrupts: Any) -> None:
        """Publish the pause. The middleware never emits, so a replayed node cannot duplicate it."""
        for item in interrupts:
            value = getattr(item, "value", None)
            if not isinstance(value, dict):
                continue
            requests = (
                ApprovalBatch.model_validate(value).approvals
                if "approvals" in value
                else [ApprovalRequest.model_validate(value)]
            )
            run.interrupt_id = str(item.id)
            run.barrier = [request.approval_id for request in requests]
            for request in requests:
                task = next(
                    (
                        task
                        for task in self.catalog.data.workspaces.tasks
                        if task.id == request.run_id
                    ),
                    None,
                )
                if task:
                    request.source_title = task.title
                    if "approval" not in task.waiting_on:
                        task.waiting_on.append("approval")
                if run.ledger:
                    record = run.ledger.announce(request, run.interrupt_id)
                    if record.status != "pending":
                        if record.answer and not any(
                            event.type == "approval.resolved"
                            and event.approval_id == request.approval_id
                            for event in run.bus.history
                        ):
                            await run.bus.emit(
                                "approval.resolved",
                                approval_id=request.approval_id,
                                decision=record.answer.decision,
                                reason=record.answer.reason,
                            )
                        continue
                run.pending = request
                if not any(
                    event.type == "approval.requested"
                    and event.approval.approval_id == request.approval_id
                    for event in run.bus.history
                ):
                    await run.bus.emit("approval.requested", approval=request)
            self.catalog.persist()

    async def _resume(self, run: Run) -> dict[str, Any]:
        if run.ledger is None:
            answer = await self._answer(run)
            return answer.model_dump(mode="json") if answer else {}
        while any(run.ledger.records[key].answer is None for key in run.barrier):
            await run.ready.wait()
            run.ready.clear()
        answers = {key: run.ledger.records[key].answer for key in run.barrier}
        value: Any = (
            {
                "answers": {
                    key: answer.model_dump(mode="json") for key, answer in answers.items() if answer
                }
            }
            if len(answers) > 1
            else next(answer.model_dump(mode="json") for answer in answers.values() if answer)
        )
        return {run.interrupt_id: value}

    async def _answer(self, run: Run) -> ApprovalAnswer | None:
        """Block until the person decides. Returns None if the run was stopped first."""
        await run.ready.wait()
        answer, run.answer = run.answer, None
        run.ready.clear()
        run.pending = None
        return answer

    async def resolve(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> None:
        if run_id not in self.runs:
            ledger, record = self.actions.find(run_id, approval_id)
            self.actions.resolve(run_id, approval_id, decision)
            if record.request.tool == "run_command" and decision.decision == "approve":
                ledger, record = self.actions.find(run_id, approval_id)
                record.execution_status = "running"
                ledger.save()
                runner = CommandRunner(
                    Path(record.request.workspace), self.redactor, secrets=self.redactor.values
                )
                result = await asyncio.to_thread(
                    runner.run,
                    str(record.request.command),
                    timeout=float(str(record.request.args.get("timeout") or 120)),
                )
                record.execution_status = "completed"
                record.result = self.redactor.text(result.model_dump_json())
                ledger.save()
            if record.request.tool == "worktree_create" and decision.decision == "approve":
                await self.start(
                    RunRequest.model_validate(record.request.args), worktree_consent=True
                )
            return
        run = self.runs[run_id]
        if run.ledger:
            if run.bus.finished or approval_id not in run.barrier:
                raise UnknownApproval(approval_id)
            record = run.ledger.records[approval_id]
            if decision.decision == "approve":
                review = prepare_review(Path(record.request.workspace), record.request)
                if decision.edited_args is not None and decision.edited_args != record.request.args:
                    raise UnknownApproval("Preview edited arguments before approval")
                if review.revision != record.request.revision:
                    raise UnknownApproval("Contents changed; refresh review")
                if decision.revision and decision.revision != review.revision:
                    raise UnknownApproval("Review was replaced; refresh before deciding")
                decision = decision.model_copy(
                    update={
                        "revision": review.revision,
                        "edited_args": record.request.args,
                    }
                )
            answer = ApprovalAnswer(approval_id=approval_id, **decision.model_dump())
            answer = ApprovalAnswer.model_validate(
                self.redactor.value(answer.model_dump(mode="json"))
            )
            if answer.decision == "approve" and decision.allow_glob:
                request = record.request
                if request.tool not in {"write_file", "edit_file"} or not request.path:
                    raise ValueError("This action cannot create an allow rule")
                expected = str(Path(request.path).parent).replace("\\", "/") + "/**"
                if decision.allow_glob != expected or request.path.startswith(".harness/"):
                    raise ValueError("Allow rule must match the reviewed source folder")
                rules = RulesEngine.load(Path(request.workspace)).rules.model_copy(deep=True)
                rules.tools.setdefault(request.tool, []).insert(
                    0, Rule(glob=decision.allow_glob, action="allow")
                )
                self.actions.propose_rules(Path(request.workspace), rules)
            run.ledger.answer(answer)
            task = next(
                (task for task in self.catalog.data.workspaces.tasks if task.id == run_id), None
            )
            if task and not any(item.status == "pending" for item in run.ledger.records.values()):
                task.waiting_on = [kind for kind in task.waiting_on if kind != "approval"]
                self.catalog.persist()
            await run.bus.emit(
                "approval.resolved",
                approval_id=approval_id,
                decision=answer.decision,
                reason=answer.reason,
            )
            run.ready.set()
            return
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

    def retry_command(self, run_id: str, call_id: str, timeout: float) -> ApprovalRecord:
        task = next(
            (item for item in self.catalog.data.workspaces.tasks if item.id == run_id), None
        )
        if task is None or not 1 <= timeout <= 600:
            raise ValueError("Unknown call or invalid timeout")
        root = workspace_root(task.worktree or task.workspace)
        log = EventBus(
            storage_path(workspace_root(task.workspace), f"runs/{run_id}/events.jsonl"),
            run_id,
            self.redactor,
        )
        call = next(
            (
                event
                for event in log.history
                if event.type == "tool.call"
                and event.call_id == call_id
                and event.name == "run_command"
            ),
            None,
        )
        if call is None or call.type != "tool.call":
            raise ValueError("Only a recorded command can be retried")
        command = str(call.args.get("command", ""))
        outcome = RulesEngine.load(root, task.mode).decide(
            "run_command", command=command, timeout=timeout
        )
        if outcome.action == "deny":
            raise ValueError("Current rules deny retry")
        return self.actions.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="command",
                tool="run_command",
                command=command,
                workspace=str(root),
                source_title=task.title,
                reason=f"Explicit command retry. Requested timeout: {timeout:g}s",
                risk=outcome.risk,
                args={"command": command, "timeout": timeout, "mode": task.mode},
            ),
        )

    def preview(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> ApprovalRequest:
        run = self.runs[run_id]
        if run.ledger is None or approval_id not in run.ledger.records:
            raise UnknownApproval(approval_id)
        record = run.ledger.records[approval_id]
        if record.status != "pending":
            raise UnknownApproval(approval_id)
        request = record.request
        args = decision.edited_args if decision.edited_args is not None else request.args
        from permissions.middleware import tool_target

        path, command, timeout = tool_target(request.tool, args)
        rules = RulesEngine.load(Path(request.workspace))
        verdict = rules.decide(request.tool, path=path, command=command, timeout=timeout)
        if verdict.action == "deny":
            raise ValueError("Current permissions deny this input")
        request = prepare_review(
            Path(request.workspace),
            request.model_copy(
                update={
                    "args": self.redactor.value(args),
                    "path": path,
                    "command": command,
                    "risk": verdict.risk,
                }
            ),
        )
        record.request = request
        run.ledger.save()
        return request

    async def stop(self, run_id: str) -> None:
        run = self.runs[run_id]
        if not run.bus.finished:
            if run.ledger:
                run.ledger.cancel()
            run.task.cancel()
            # Report cancellation before SQLite/HTTP cleanup. Terminal buses reject
            # late events, so cleanup cannot append results or another finish.
            await run.bus.emit("run.finished", status="stopped")

    def events(self, run_id: str, after: int) -> AsyncIterator[Event]:
        return self.runs[run_id].bus.events(after)

    async def close(self) -> None:
        for run in self.runs.values():
            run.preserving = True
            run.task.cancel()
        await asyncio.gather(*(run.task for run in self.runs.values()), return_exceptions=True)
