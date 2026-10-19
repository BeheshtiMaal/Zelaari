"""Permission and approval contracts. Leaf module: imports nothing from the engine."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

Mode = Literal["read-only", "ask", "auto"]
"""Conversation ceiling.

Read-only denies every mutation; auto relaxes defaults, not the always-ask list.
"""


class UnknownApproval(Exception):
    """The approval id is not pending for this run, or was already answered."""


Action = Literal["allow", "ask", "deny"]
RiskLevel = Literal["low", "high"]


class PermissionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rule(PermissionModel):
    """One row of the rules grid: a path glob (or `*` for whole-tool) mapped to an action."""

    glob: str = Field(default="*", min_length=1, max_length=512)
    action: Action

    @field_validator("glob")
    @classmethod
    def no_traversal(cls, value: str) -> str:
        if ".." in value.replace("**", ""):
            raise ValueError("Globs are workspace-relative and cannot contain '..'")
        return value


class RulesFile(PermissionModel):
    """`.harness/rules.json`. Unknown keys are rejected so a typo cannot silently disable a rule."""

    version: int = Field(default=1, ge=1, le=1)
    mode: Mode = "ask"
    tools: dict[str, list[Rule]] = Field(default_factory=dict)


class RiskAssessment(PermissionModel):
    level: RiskLevel = "low"
    reasons: list[str] = Field(default_factory=list)


class ApprovalRequest(PermissionModel):
    """Payload of `approval.requested`.

    `approval_id` is the tool call id, so it stays stable across a resume.
    """

    approval_id: str
    run_id: str
    kind: Literal["tool", "command"]
    tool: str
    path: str | None = None
    command: str | None = None
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    reason: str = ""
    args: dict[str, JsonValue] = Field(default_factory=dict)
    workspace: str = ""
    source_title: str = ""
    source_kind: Literal["task", "schedule", "configuration"] = "task"
    agent_reason: str | None = None
    policy_code: str = "permission_required"
    diff: str = ""
    revision: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalDecision(PermissionModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=2000)
    edited_args: dict[str, JsonValue] | None = None
    allow_glob: str | None = Field(default=None, max_length=512)
    revision: str | None = None


class ApprovalAnswer(ApprovalDecision):
    """The resume value for one interrupt.

    `approval_id` is carried so a resumed run cannot apply a decision to the wrong
    call if a turn ever holds more than one pending approval.
    """

    approval_id: str


class ApprovalBatch(PermissionModel):
    """One graph barrier containing independent, identity-bound human decisions."""

    approvals: list[ApprovalRequest]


class ApprovalBatchAnswer(PermissionModel):
    answers: dict[str, ApprovalAnswer]


class ApprovalRecord(PermissionModel):
    request: ApprovalRequest
    interrupt_id: str
    status: Literal["pending", "approved", "rejected", "cancelled"] = "pending"
    answer: ApprovalAnswer | None = None
    resolved_at: datetime | None = None
    execution_status: Literal["not_started", "running", "completed", "interrupted"] = "not_started"
    result: str | None = None


class CommandJournalEntry(PermissionModel):
    call_id: str
    args_digest: str
    status: Literal["intent", "completed", "interrupted"] = "intent"
    result: str | None = None


class PermissionOutcome(PermissionModel):
    """The resolved verdict for one tool call, before execution."""

    action: Action
    reason: str = ""
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    edited_args: dict[str, JsonValue] | None = None
    revision: str | None = None
