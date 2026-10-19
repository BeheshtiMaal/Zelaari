"""Wire contract. Generate the renderer types from these Pydantic schemas."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from permissions.types import ApprovalDecision, ApprovalRecord, ApprovalRequest
from providers.base import ModelInput, Preset, ProviderRecord, Settings, WorkspaceState
from tools.types import (
    BranchList,
    BranchSwitch,
    BranchSwitchResult,
    CommandResult,
    FileListing,
    RevertResult,
    RulesResponse,
    SnapshotEntry,
)


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventBase(WireModel):
    run_id: str
    seq: int = Field(ge=1)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunStarted(EventBase):
    type: Literal["run.started"] = "run.started"
    task: str
    model: str


class MessageDelta(EventBase):
    type: Literal["message.delta"] = "message.delta"
    message_id: str
    text: str


class ToolCall(EventBase):
    type: Literal["tool.call"] = "tool.call"
    call_id: str
    name: str
    args: dict[str, JsonValue]


class ToolResult(EventBase):
    type: Literal["tool.result"] = "tool.result"
    call_id: str
    text: str


class RunFinished(EventBase):
    type: Literal["run.finished"] = "run.finished"
    status: Literal["completed", "stopped", "error"]


class RunError(EventBase):
    type: Literal["run.error"] = "run.error"
    message: str


class ApprovalRequested(EventBase):
    """One tool call needs a human decision before it runs."""

    type: Literal["approval.requested"] = "approval.requested"
    approval: ApprovalRequest


class ApprovalResolved(EventBase):
    type: Literal["approval.resolved"] = "approval.resolved"
    approval_id: str
    decision: Literal["approve", "reject"]
    reason: str | None = None


class FutureEvent(EventBase):
    """Reserved events: not emitted by the Phase 3 bridge."""

    type: Literal[
        "plan.created",
        "plan.step.updated",
        "subagent.started",
        "subagent.finished",
        "context.summarized",
        "question.asked",
        "question.answered",
        "ui.render",
        "test.result",
    ]
    data: dict[str, JsonValue]


class ReasoningDelta(EventBase):
    type: Literal["reasoning.delta"] = "reasoning.delta"
    message_id: str
    text: str


class UsageUpdated(EventBase):
    type: Literal["usage.updated"] = "usage.updated"
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated: bool


Event = Annotated[
    RunStarted
    | MessageDelta
    | ReasoningDelta
    | UsageUpdated
    | ToolCall
    | ToolResult
    | ApprovalRequested
    | ApprovalResolved
    | RunFinished
    | RunError
    | FutureEvent,
    Field(discriminator="type"),
]
event_adapter: TypeAdapter[Event] = TypeAdapter(Event)


class RunRequest(WireModel):
    task: str = Field(min_length=1, max_length=32000)
    workspace: str
    model: str = Field(default="demo", pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    mode: Literal["read-only", "ask", "auto"] = "ask"
    worktree: bool = False
    worktree_approved: bool = False
    """Set only after the person confirmed the worktree approval.

    Creating a worktree writes to `.harness/` and adds a branch, so it is a gated
    action: a run that asks for one without this flag is refused rather than quietly
    skipped.
    """


class RunResponse(WireModel):
    run_id: str


class HealthResponse(WireModel):
    status: Literal["ok"] = "ok"


class Protocol(WireModel):
    """Schema-generation envelope only; never sent over the wire."""

    event: Event
    run_request: RunRequest
    run_response: RunResponse
    health: HealthResponse
    model_input: ModelInput
    provider: ProviderRecord
    settings: Settings
    preset: Preset
    workspaces: WorkspaceState
    approval_request: ApprovalRequest
    approval_decision: ApprovalDecision
    approval_record: ApprovalRecord
    command_result: CommandResult
    file_listing: FileListing
    revert_result: RevertResult
    snapshot_entry: SnapshotEntry
    branch_switch: BranchSwitch
    branch_switch_result: BranchSwitchResult
    branch_list: BranchList
    rules_response: RulesResponse
