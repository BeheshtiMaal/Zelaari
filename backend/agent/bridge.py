"""Consume deepagents streams into durable, replayable harness events."""

import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.activity import finish_open_activity, open_activity
from agent.events import Event, RunRequest
from agent.factory import build_agent
from agent.meter import TokenMeter
from agent.projection import ActivityProjection
from agent.steering import SteeringMiddleware
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
from planning.gate import record_from_state
from planning.publication import publish_plan
from planning.types import ActivityScope, SteeringRecord, SteeringSubmission
from providers.adapters import chat_model
from providers.base import ProviderRecord, TaskRecord
from providers.context import detect_context
from providers.demo import DemoModel
from questions.types import HumanBatch, QuestionAnswer, QuestionDecision, QuestionRecord
from store.actions import ActionApprovals
from store.approvals import ApprovalLedger
from store.catalog import Catalog
from store.eventlog import EventBus
from store.questions import QuestionLedger
from store.secrets import Redactor
from store.steering import SteeringQueue
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
    available: asyncio.Event = field(default_factory=asyncio.Event)
    questions: QuestionLedger | None = None
    question_barrier: list[str] = field(default_factory=list)
    human_barrier: bool = False
    steering: SteeringQueue | None = None
    cleanup: asyncio.Task[None] | None = None
    runner: CommandRunner | None = None


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
        self.actions.recover()
        # Recovery runs on every polled request, so two overlapping calls must never start a
        # second graph invocation for one run: that duplicates checkpoints and can leave a
        # suspended invocation holding the workspace's SQLite connection open.
        self.starting = asyncio.Lock()

    def contains(self, run_id: str) -> bool:
        return run_id in self.runs or any(
            record.request.run_id == run_id for record in self.actions.records()
        )

    def pending_paths(self) -> set[str]:
        """Paths a paused run is waiting on, so the file viewer can badge them."""
        paths = {
            run.pending.path.replace("\\", "/")
            for run in self.runs.values()
            if run.ledger is None and run.pending is not None and run.pending.path
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
        self,
        request: RunRequest,
        *,
        restore_id: str | None = None,
        worktree_consent: bool = False,
        allocated_id: str | None = None,
    ) -> str:
        async with self.starting:
            if restore_id and restore_id in self.runs:
                return restore_id
            return await self._start(
                request,
                restore_id=restore_id,
                worktree_consent=worktree_consent,
                allocated_id=allocated_id,
            )

    async def _start(
        self,
        request: RunRequest,
        *,
        restore_id: str | None = None,
        worktree_consent: bool = False,
        allocated_id: str | None = None,
    ) -> str:
        workspace = workspace_root(request.workspace)
        record = self.catalog.require(request.model)
        if restore_id:
            provider_path = storage_path(workspace, f"runs/{restore_id}/provider.json")
            saved_provider = ProviderRecord.model_validate_json(provider_path.read_bytes())
            if (record.base_url, record.model, record.kind) != (
                saved_provider.base_url,
                saved_provider.model,
                saved_provider.kind,
            ):
                raise ValueError("Restore the original model configuration before resuming")
        model = (
            DemoModel(delay=self.demo_delay, locale=self.catalog.data.settings.locale)
            if record.kind == "demo"
            else chat_model(record, self.catalog.keys[request.model])
        )
        run_id = restore_id or allocated_id or uuid4().hex
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
        questions = QuestionLedger(storage_path(workspace, f"runs/{run_id}/questions.json"))
        steering = SteeringQueue(storage_path(workspace, f"runs/{run_id}/steering.json"), run_id)
        safe_task = self.redactor.text(request.task)
        grill = bool(re.match(r"^/grill(?:\s|$)", safe_task))
        if not restore_id:
            from tools.atomic import atomic_write

            atomic_write(
                storage_path(workspace, f"runs/{run_id}/provider.json"), record.model_dump_json()
            )

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
            prompt = Path(__file__).with_name("genui_prompt.txt").read_text(encoding="utf-8")
            meter = TokenMeter(len(safe_task) + len(prompt))
            previous_usage = next(
                (event for event in reversed(bus.history) if event.type == "usage.updated"), None
            )
            if previous_usage:
                meter.input_tokens = previous_usage.input_tokens
                meter.output_tokens = previous_usage.output_tokens
                meter.estimated = previous_usage.estimated
            projection = ActivityProjection(
                bus, meter, record.context.tokens, record.context.estimated
            )
            try:
                async with AsyncSqliteSaver.from_conn_string(str(checkpoint)) as saver:
                    rules = RulesEngine.load(root, request.mode)
                    runner = CommandRunner(root, self.redactor, secrets=self.redactor.values)
                    run.runner = runner
                    graph = build_agent(
                        root,
                        model,
                        saver,
                        self.redactor,
                        permissions=PermissionMiddleware(
                            rules, run_id=run_id, redactor=self.redactor, grill=grill
                        ),
                        snapshots=SnapshotStore(root, run_id=run_id, redactor=self.redactor),
                        extra_tools=[
                            build_run_command(runner),
                            build_git_switch(root),
                        ],
                        grill=grill,
                        bus=bus,
                        model_name=record.model,
                        provider_name=record.name,
                        cancelled=runner.cancelled,
                        extra_middleware=[SteeringMiddleware(steering)],
                    )
                    config: RunnableConfig = {
                        "configurable": {"thread_id": run_id},
                        "recursion_limit": 256,
                    }
                    payload: Any = {"messages": [{"role": "user", "content": safe_task}]}
                    if restore_id:
                        await finish_open_activity(bus, "interrupted")
                        snapshot = await graph.aget_state(config)
                        if not snapshot.values:
                            raise ValueError("Checkpoint is unavailable; refusing a new invocation")
                        await publish_plan(bus, record_from_state(snapshot.values))
                        steering.reconcile(snapshot.values)
                        await steering.publish(bus)
                        if snapshot.values.get("activity_scope") and snapshot.next:
                            scope = ActivityScope.model_validate(snapshot.values["activity_scope"])
                            scope = scope.model_copy(update={"scope_id": uuid4().hex})
                            projection.scopes[()] = scope
                            await bus.emit("activity.started", scope=scope)
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
                            if mode == "messages":
                                chunk, _metadata = update
                                if (
                                    isinstance(chunk, AIMessageChunk)
                                    and _metadata.get("lc_source") != "summarization"
                                ):
                                    await projection.content(namespace, chunk, False)
                            elif mode == "updates" and "__interrupt__" not in update:
                                for change in update.values():
                                    if isinstance(change, dict):
                                        steering.reconcile(change)
                                await steering.publish(bus)
                                await projection.update(namespace, update)

                        # An interrupt ends the stream but not the run: the graph still
                        # has a node to re-execute once the decision arrives.
                        snapshot = await graph.aget_state(config)
                        await publish_plan(bus, record_from_state(snapshot.values))
                        steering.reconcile(snapshot.values)
                        await steering.publish(bus)
                        if not snapshot.next:
                            if steering.pending():
                                payload = {"messages": []}
                                continue
                            break
                        await self._announce(run, snapshot.interrupts)
                        payload = Command(resume=await self._resume(run))
                await finish_open_activity(bus, "completed")
                await bus.emit("run.finished", status="completed")
            except asyncio.CancelledError:
                if not run.preserving:
                    await finish_open_activity(bus, "cancelled")
                    await bus.emit("run.finished", status="stopped")
            except Exception as error:
                await finish_open_activity(bus, "failed")
                steering.cancel()
                await steering.publish(bus)
                if run.ledger:
                    run.ledger.cancel()
                if run.questions:
                    run.questions.cancel()
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
                run.available.set()
                final = bus.history[-1]
                if final.type == "run.finished":
                    task_record.status = final.status
                    task_record.waiting_on = []
                self.catalog.persist()

        self.runs[run_id] = Run(
            bus,
            asyncio.create_task(execute()),
            ledger=ledger,
            questions=questions,
            steering=steering,
        )
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
                    if (
                        bus.history[-1].type == "run.finished"
                        and bus.history[-1].status == "stopped"
                    ):
                        ApprovalLedger(path.with_name("approvals.json")).cancel()
                        QuestionLedger(path.with_name("questions.json")).cancel()
                        SteeringQueue(path.with_name("steering.json"), item.id).cancel()
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
                active_run = self.runs.get(task.id)
                if active_run and active_run.ledger:
                    result.extend(
                        record
                        for record in active_run.ledger.records.values()
                        if status is None or record.status == status
                    )
                    continue
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
    def questions(self, run_id: str) -> list[QuestionRecord]:
        active = self.runs.get(run_id)
        if active and active.questions:
            return list(active.questions.records.values())
        task = next(
            (task for task in self.catalog.data.workspaces.tasks if task.id == run_id), None
        )
        if task is None:
            raise ValueError("Unknown question run")
        return list(
            QuestionLedger(
                storage_path(workspace_root(task.workspace), f"runs/{run_id}/questions.json")
            ).records.values()
        )

    def _waiting(self, run: Run) -> None:
        task = next(
            (task for task in self.catalog.data.workspaces.tasks if task.id == run.bus.run_id), None
        )
        if task:
            task.waiting_on = []
            if run.ledger and any(
                record.status == "pending" for record in run.ledger.records.values()
            ):
                task.waiting_on.append("approval")
            if run.questions and any(
                record.status == "pending" for record in run.questions.records.values()
            ):
                task.waiting_on.append("question")
            self.catalog.persist()

    async def answer_question(self, run_id: str, call_id: str, decision: QuestionDecision) -> None:
        if run_id not in self.runs:
            raise ValueError("Question run is unavailable")
        run = self.runs[run_id]
        await asyncio.wait_for(run.available.wait(), timeout=30)
        if run.bus.finished or call_id not in run.question_barrier or not run.questions:
            raise ValueError("Question is not pending")
        answer = QuestionAnswer.model_validate(
            self.redactor.value(
                {**decision.model_dump(mode="json"), "run_id": run_id, "call_id": call_id}
            )
        )
        run.questions.answer(answer)
        self._waiting(run)
        await run.bus.emit("question.answered", answer=answer)
        run.ready.set()

    async def _announce(self, run: Run, interrupts: Any) -> None:
        """Publish the pause. The middleware never emits, so a replayed node cannot duplicate it."""
        for item in interrupts:
            value = getattr(item, "value", None)
            if not isinstance(value, dict):
                continue
            run.human_barrier = value.get("kind") == "human"
            run.question_barrier = []
            if run.human_barrier:
                batch = HumanBatch.model_validate(value)
                if run.questions is None:
                    raise ValueError("Missing question ledger")
                for question_request in batch.questions:
                    question_record = run.questions.announce(question_request, str(item.id))
                    run.question_barrier.append(question_request.call_id)
                    if not any(
                        event.type == "question.asked"
                        and event.question.request.call_id == question_request.call_id
                        for event in run.bus.history
                    ):
                        await run.bus.emit(
                            "question.asked", question=question_record.model_copy(deep=True)
                        )
                    if question_record.answer and not any(
                        event.type == "question.answered"
                        and event.answer.call_id == question_request.call_id
                        for event in run.bus.history
                    ):
                        await run.bus.emit("question.answered", answer=question_record.answer)
            requests = (
                HumanBatch.model_validate(value).approvals
                if run.human_barrier
                else ApprovalBatch.model_validate(value).approvals
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
            self._waiting(run)
            self.catalog.persist()
            run.available.set()

    async def _resume(self, run: Run) -> dict[str, Any]:
        if run.ledger is None:
            answer = await self._answer(run)
            return answer.model_dump(mode="json") if answer else {}
        while any(run.ledger.records[key].answer is None for key in run.barrier) or (
            run.questions is not None
            and any(run.questions.records[key].answer is None for key in run.question_barrier)
        ):
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
            else next((answer.model_dump(mode="json") for answer in answers.values() if answer), {})
        )
        if run.human_barrier:
            value = {
                "kind": "human",
                "approvals": {
                    key: answer.model_dump(mode="json") for key, answer in answers.items() if answer
                },
                "questions": {
                    key: cast(QuestionAnswer, run.questions.records[key].answer).model_dump(
                        mode="json"
                    )
                    for key in run.question_barrier
                    if run.questions and run.questions.records[key].answer
                },
            }
        run.pending = None
        return {run.interrupt_id: value}

    async def _answer(self, run: Run) -> ApprovalAnswer | None:
        """Block until the person decides. Returns None if the run was stopped first."""
        await run.ready.wait()
        answer, run.answer = run.answer, None
        run.ready.clear()
        run.pending = None
        return answer

    async def resolve(
        self, run_id: str, approval_id: str, decision: ApprovalDecision
    ) -> str | None:
        if run_id not in self.runs:
            ledger, record = self.actions.find(run_id, approval_id)
            self.actions.resolve(run_id, approval_id, decision)
            if record.request.tool == "run_command" and decision.decision == "approve":
                _, record = self.actions.find(run_id, approval_id)
                self.actions.execution(run_id, approval_id, "running")
                runner = CommandRunner(
                    Path(record.request.workspace), self.redactor, secrets=self.redactor.values
                )
                result = await asyncio.to_thread(
                    runner.run,
                    str(record.request.command),
                    timeout=float(str(record.request.args.get("timeout") or 120)),
                )
                self.actions.execution(run_id, approval_id, "completed", result.model_dump_json())
            if record.request.tool == "worktree_create" and decision.decision == "approve":
                self.actions.execution(run_id, approval_id, "running")
                created_id = await self.start(
                    RunRequest.model_validate(record.request.args),
                    worktree_consent=True,
                    allocated_id=Path(str(record.request.path)).name,
                )
                self.actions.execution(
                    run_id, approval_id, "completed", f"Worktree: {record.request.path}"
                )
                return created_id
            return None
        run = self.runs[run_id]
        if run.ledger:
            if not run.barrier and not run.bus.finished:
                await asyncio.wait_for(run.available.wait(), timeout=30)
            if run.bus.finished or approval_id not in run.barrier:
                raise UnknownApproval(approval_id)
            record = run.ledger.records[approval_id]
            if record.status != "pending":
                raise UnknownApproval(approval_id)
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
            return None
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
        return None

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
        if run_id not in self.runs:
            return self.actions.preview(run_id, approval_id, decision)
        run = self.runs[run_id]
        if run.ledger is None or approval_id not in run.ledger.records:
            raise UnknownApproval(approval_id)
        record = run.ledger.records[approval_id]
        if record.status != "pending":
            raise UnknownApproval(approval_id)
        request = record.request
        args = decision.edited_args if decision.edited_args is not None else request.args
        if self.redactor.value(args) != args:
            raise ValueError("Secret in edited arguments")
        from permissions.middleware import tool_target

        path, command, timeout = tool_target(request.tool, args)
        task = next(
            (item for item in self.catalog.data.workspaces.tasks if item.id == run_id), None
        )
        rules = RulesEngine.load(Path(request.workspace), task.mode if task else None)
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
        request = ApprovalRequest.model_validate(
            self.redactor.value(request.model_dump(mode="json"))
        )
        record.request = request
        run.ledger.save()
        return request

    async def stop(self, run_id: str) -> None:
        run = self.runs[run_id]
        if not run.bus.finished:
            if run.runner:
                run.runner.cancel()
            if run.ledger:
                run.ledger.cancel(persist=False)
            if run.questions:
                run.questions.cancel(persist=False)
            if run.steering:
                run.steering.cancel(persist=False)
            run.task.cancel()
            # Report cancellation before SQLite/HTTP cleanup. Terminal buses reject
            # late events, so cleanup cannot append results or another finish.
            events: list[tuple[str, dict[str, Any]]] = [
                (kind.replace("started", "finished"), {"scope": scope, "status": "cancelled"})
                for kind, scope in open_activity(run.bus)
            ]
            if run.steering:
                events.extend(
                    ("steering.updated", {"message": record})
                    for record in run.steering.records
                    if record.status == "cancelled"
                )
            events.append(("run.finished", {"status": "stopped"}))
            await run.bus.emit_many(events)

            async def cleanup() -> None:
                for ledger in (run.ledger, run.questions, run.steering):
                    if ledger:
                        await asyncio.to_thread(ledger.save)

            run.cleanup = asyncio.create_task(cleanup())

    async def steer(self, run_id: str, value: SteeringSubmission) -> SteeringRecord:
        run = self.runs.get(run_id)
        if run is None or run.steering is None:
            raise ValueError("Run has no steering queue")
        if self.redactor.text(value.submission_id) != value.submission_id:
            raise ValueError("Secret in submission identity")
        safe = value.model_copy(update={"text": self.redactor.text(value.text)})
        record = run.steering.enqueue(safe, terminal=run.bus.finished)
        await run.steering.publish(run.bus)
        return record

    def events(self, run_id: str, after: int) -> AsyncIterator[Event]:
        return self.runs[run_id].bus.events(after)

    async def close(self) -> None:
        for run in self.runs.values():
            run.preserving = True
            if run.runner:
                run.runner.cancel()
            run.task.cancel()
        await asyncio.gather(*(run.task for run in self.runs.values()), return_exceptions=True)
        await asyncio.gather(*(run.cleanup for run in self.runs.values() if run.cleanup))
