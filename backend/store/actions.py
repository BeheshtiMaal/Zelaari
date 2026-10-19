"""Durable approvals for user-initiated configuration changes, without a model run."""

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Literal, cast
from uuid import uuid4

from permissions.review import prepare_review
from permissions.rules import RulesEngine
from permissions.types import (
    ApprovalAnswer,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    Mode,
    RulesFile,
    UnknownApproval,
)
from planning.policy import merged_settings
from planning.types import PlanningSettings
from store.approvals import ApprovalLedger
from store.catalog import Catalog
from store.workspaces import select_workspace
from tools.atomic import atomic_write
from tools.git import switch, validate_branch
from tools.jail import resolve_virtual, storage_path, workspace_root
from tools.snapshot import SnapshotError, SnapshotStore

_lock = RLock()


def serialized[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    @wraps(function)
    def execute(*args: P.args, **kwargs: P.kwargs) -> T:
        with _lock:
            return function(*args, **kwargs)

    return execute


class ActionApprovals:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def ledgers(self) -> list[ApprovalLedger]:
        result = []
        for workspace in self.catalog.data.workspaces.recent:
            try:
                result.append(
                    ApprovalLedger(
                        storage_path(workspace_root(workspace.path), "action-approvals.json")
                    )
                )
            except (OSError, ValueError):
                continue
        return result

    @serialized
    def records(self) -> list[ApprovalRecord]:
        return [record for ledger in self.ledgers() for record in ledger.records.values()]

    @serialized
    def recover(self) -> None:
        for ledger in self.ledgers():
            changed = False
            for record in ledger.records.values():
                if record.execution_status == "running":
                    record.execution_status = "interrupted"
                    record.result = "Interrupted: this action may have run. It was not replayed."
                    changed = True
            if changed:
                ledger.save()

    @serialized
    def find(self, run_id: str, approval_id: str) -> tuple[ApprovalLedger, ApprovalRecord]:
        for ledger in self.ledgers():
            record = ledger.records.get(approval_id)
            if record and record.request.run_id == run_id:
                return ledger, record
        raise UnknownApproval(approval_id)

    @serialized
    def preview(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> ApprovalRequest:
        ledger, record = self.find(run_id, approval_id)
        if record.status != "pending":
            raise UnknownApproval(approval_id)
        request = record.request
        root = workspace_root(request.workspace)
        args = decision.edited_args if decision.edited_args is not None else request.args
        if self.catalog.redactor.value(args) != args:
            raise ValueError("Secret in proposed arguments")
        if request.tool == "planning_settings_update":
            if set(args) != {"content"}:
                raise ValueError("Invalid planning settings input")
            request = request.model_copy(update={"args": args})
        elif request.tool == "rules_update":
            if set(args) not in ({"content"}, {"content", "remove"}):
                raise ValueError("Invalid rules input")
            if args.get("remove") is True:
                if args["content"] != "":
                    raise ValueError("Removing rules cannot include replacement content")
            else:
                RulesFile.model_validate_json(str(args["content"]))
            request = request.model_copy(update={"args": args})
        elif request.tool in {"run_command", "git_switch"}:
            mode = request.args.get("mode")
            if args.get("mode") != mode:
                raise ValueError("Permission mode cannot be raised by editing arguments")
            if request.tool == "run_command":
                if set(args) - {"command", "timeout", "mode"}:
                    raise ValueError("Unknown command arguments")
                command = args.get("command")
                timeout = args.get("timeout", 120)
                if (
                    not isinstance(command, str)
                    or not command
                    or not isinstance(timeout, int | float)
                    or not 1 <= timeout <= 600
                ):
                    raise ValueError("Invalid command or timeout")
            else:
                if set(args) - {"branch", "mode"}:
                    raise ValueError("Unknown branch arguments")
                command = f"git switch {validate_branch(str(args.get('branch', '')))}"
                timeout = 120
            verdict = RulesEngine.load(root, cast(Mode | None, mode)).decide(
                request.tool, command=command, timeout=timeout
            )
            if verdict.action == "deny":
                raise ValueError("Current rules deny edited arguments")
            request = request.model_copy(
                update={
                    "args": args,
                    "command": command,
                    "risk": verdict.risk,
                }
            )
        else:
            raise ValueError("Create a new worktree proposal to change its input")
        prepared = prepare_review(root, request)
        record.request = ApprovalRequest.model_validate(
            self.catalog.redactor.value(prepared.model_dump(mode="json"))
        )
        ledger.save()
        return record.request

    def propose_rules(
        self, root: Path, value: RulesFile, *, raw_content: str | None = None, remove: bool = False
    ) -> ApprovalRecord:
        engine = RulesEngine.load(root)
        if engine.load_error:
            raise ValueError("Repair the unreadable rules file before proposing changes")
        if raw_content is not None:
            RulesFile.model_validate_json(raw_content)
        content = (
            ""
            if remove
            else raw_content
            if raw_content is not None
            else value.model_dump_json(indent=2)
        )
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in rules")
        select_workspace(self.catalog, str(root))
        identity = uuid4().hex
        request = prepare_review(
            root,
            ApprovalRequest(
                approval_id=identity,
                run_id=f"configuration-{identity}",
                kind="tool",
                tool="rules_update",
                path=".harness/rules.json",
                workspace=str(root),
                source_kind="configuration",
                source_title="Rules and permissions",
                reason="Changes to workspace permissions always require approval",
                policy_code="rules_change",
                args={"content": content, **({"remove": True} if remove else {})},
            ),
        )
        return self.propose(root, request)

    def propose_planning(self, root: Path, value: PlanningSettings) -> ApprovalRecord:
        content = merged_settings(root, value)
        if self.catalog.redactor.text(content) != content:
            raise ValueError("Secret in workspace configuration")
        return self.propose(
            root,
            ApprovalRequest(
                approval_id="",
                run_id="",
                kind="tool",
                tool="planning_settings_update",
                path=".harness/config.json",
                source_kind="configuration",
                source_title="Planning settings",
                policy_code="planning_settings_change",
                reason="Changes to engine configuration always require approval",
                args={"content": content},
            ),
        )

    @serialized
    def propose(self, root: Path, request: ApprovalRequest) -> ApprovalRecord:
        request = ApprovalRequest.model_validate(
            self.catalog.redactor.value(request.model_dump(mode="json"))
        )
        select_workspace(self.catalog, str(root))
        identity = uuid4().hex
        request = prepare_review(
            root,
            request.model_copy(
                update={
                    "approval_id": identity,
                    "run_id": f"configuration-{identity}",
                    "workspace": str(root),
                }
            ),
        )
        ledger = ApprovalLedger(storage_path(root, "action-approvals.json"))
        request = ApprovalRequest.model_validate(
            self.catalog.redactor.value(request.model_dump(mode="json"))
        )
        return ledger.announce(request, request.run_id)

    @serialized
    def execution(
        self,
        run_id: str,
        approval_id: str,
        status: Literal["running", "completed", "interrupted"],
        result: str | None = None,
    ) -> None:
        ledger, record = self.find(run_id, approval_id)
        record.execution_status = status
        record.result = self.catalog.redactor.text(result) if result else None
        ledger.save()

    @serialized
    def resolve(self, run_id: str, approval_id: str, decision: ApprovalDecision) -> None:
        decision = ApprovalDecision.model_validate(
            self.catalog.redactor.value(decision.model_dump(mode="json"))
        )
        ledger, record = self.find(run_id, approval_id)
        if record.status != "pending":
            raise UnknownApproval(approval_id)
        request = record.request
        root = workspace_root(request.workspace)
        if decision.decision == "approve":
            if decision.edited_args is not None:
                raise ValueError("Edit the rules grid and submit a new proposal")
            current = prepare_review(root, request)
            if current.revision != request.revision:
                raise ValueError("Rules changed; submit a fresh proposal")
            if decision.revision and decision.revision != current.revision:
                raise ValueError("Review changed; refresh before approving")
            if request.tool in {"git_switch", "run_command"}:
                mode = request.args.get("mode")
                if mode is not None and mode not in {"ask", "auto", "read-only"}:
                    raise ValueError("Invalid permission mode")
                outcome = RulesEngine.load(root, cast(Mode | None, mode)).decide(
                    request.tool,
                    command=request.command,
                    timeout=float(str(request.args.get("timeout") or 120)),
                )
                if outcome.action == "deny":
                    raise ValueError("Current rules deny branch switching")
                record.execution_status = "running"
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                if request.tool == "run_command":
                    return
                result = switch(root, str(request.args["branch"]))
                if result.error:
                    record.execution_status = "interrupted"
                    record.result = self.catalog.redactor.text(result.error)
                    ledger.save()
                    raise ValueError("Git refused branch switching")
                record.execution_status = "completed"
                record.result = f"Branch: {result.branch}"
                ledger.save()
                return
            if request.tool == "worktree_create":
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                return
            remove = request.args.get("remove") is True
            planning = request.tool == "planning_settings_update"
            if not remove and not planning:
                RulesFile.model_validate_json(str(request.args["content"]))
            # An answer is durable before mutation. If the process dies in between,
            # the proposal stays decided and is never automatically applied again.
            record.execution_status = "running"
            ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
            try:
                SnapshotStore(root, redactor=self.catalog.redactor).capture(
                    resolve_virtual(
                        root,
                        ".harness/config.json" if planning else ".harness/rules.json",
                        allow_protected=True,
                    ),
                    tool="planning_settings_update" if planning else "rules_update",
                    call_id=approval_id,
                )
                target = storage_path(root, "config.json" if planning else "rules.json")
                if remove:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, str(request.args["content"]))
            except (SnapshotError, OSError):
                record.execution_status = "interrupted"
                record.result = "Rules were not saved; inspect credentials and file permissions."
                ledger.save()
                raise ValueError(record.result) from None
            record.execution_status = "completed"
            record.result = "Planning settings saved." if planning else "Rules saved."
            ledger.save()
        else:
            ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
