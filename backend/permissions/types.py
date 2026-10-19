"""Permission and approval contracts. Leaf module: imports nothing from the engine."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Mode = Literal["read-only", "ask", "auto"]
"""Conversation ceiling.

Read-only denies every mutation; auto relaxes defaults, not the always-ask list.
"""

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


class ApprovalDecision(PermissionModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=2000)


class PermissionOutcome(PermissionModel):
    """The resolved verdict for one tool call, before execution."""

    action: Action
    reason: str = ""
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
