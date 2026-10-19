"""Durable approvals for user-initiated configuration changes, without a model run."""

from pathlib import Path
from typing import cast
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
from store.approvals import ApprovalLedger
from store.catalog import Catalog
from store.workspaces import select_workspace
from tools.git import switch
from tools.jail import resolve_virtual, storage_path, workspace_root
from tools.snapshot import SnapshotStore


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

    def records(self) -> list[ApprovalRecord]:
        return [record for ledger in self.ledgers() for record in ledger.records.values()]

    def find(self, run_id: str, approval_id: str) -> tuple[ApprovalLedger, ApprovalRecord]:
        for ledger in self.ledgers():
            record = ledger.records.get(approval_id)
            if record and record.request.run_id == run_id:
                return ledger, record
        raise UnknownApproval(approval_id)

    def propose_rules(self, root: Path, value: RulesFile) -> ApprovalRecord:
        engine = RulesEngine.load(root)
        if engine.load_error:
            raise ValueError("Repair the unreadable rules file before proposing changes")
        content = value.model_dump_json(indent=2)
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
                args={"content": content},
            ),
        )
        return self.propose(root, request)

    def propose(self, root: Path, request: ApprovalRequest) -> ApprovalRecord:
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
        return ledger.announce(request, request.run_id)

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
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                if request.tool == "run_command":
                    return
                result = switch(root, str(request.args["branch"]))
                if result.error:
                    raise ValueError("Git refused branch switching")
                return
            if request.tool == "worktree_create":
                ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
                return
            value = RulesFile.model_validate_json(str(request.args["content"]))
            # An answer is durable before mutation. If the process dies in between,
            # the proposal stays decided and is never automatically applied again.
            ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
            SnapshotStore(root).capture(
                resolve_virtual(root, ".harness/rules.json", allow_protected=True),
                tool="rules_update",
                call_id=approval_id,
            )
            RulesEngine.load(root).save(value)
        else:
            ledger.answer(ApprovalAnswer(approval_id=approval_id, **decision.model_dump()))
