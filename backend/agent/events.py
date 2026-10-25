"""Wire contract. Generate the renderer types from these Pydantic schemas."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from appdata.types import AppInfo, DataSummary, DeletedRuns
from permissions.types import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalResolution,
    RulesFile,
)
from planning.types import (
    ActivityScope,
    PlanningSettings,
    PlanRecord,
    SteeringRecord,
    SteeringSubmission,
    StepProgress,
)
from providers.base import ModelInput, Preset, ProviderRecord, Settings, WorkspaceState
from questions.types import QuestionAnswer, QuestionDecision, QuestionRecord, QuestionRequest
from skills.types import (
    AgentDocument,
    AgentRecord,
    AgentWriteInput,
    ConnectorList,
    ConnectorStatus,
    CustomizeSettings,
    MarketplaceCatalog,
    McpServerInput,
    MemoryDocument,
    SkillCommand,
    SkillDetail,
    SkillRecord,
    SkillsResponse,
)
from tools.types import (
    BranchList,
    BranchSwitch,
    BranchSwitchResult,
    CommandResult,
    FileListing,
    RevertResult,
    RulesResponse,
    RunFileList,
    SnapshotEntry,
)
from verify.context import ContextBreakdown
from verify.results import TestOutcome
from verify.settings import VerifyConfig, VerifySettingsResponse


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
    scope: ActivityScope | None = None


class ToolCall(EventBase):
    type: Literal["tool.call"] = "tool.call"
    call_id: str
    name: str
    args: dict[str, JsonValue]
    scope: ActivityScope | None = None


class ToolResult(EventBase):
    type: Literal["tool.result"] = "tool.result"
    call_id: str
    text: str
    scope: ActivityScope | None = None


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


class QuestionAsked(EventBase):
    type: Literal["question.asked"] = "question.asked"
    question: QuestionRecord


class QuestionAnswered(EventBase):
    type: Literal["question.answered"] = "question.answered"
    answer: QuestionAnswer


class UiRender(EventBase):
    """One rendering attempt: the program, whether it rendered, and why it did not.

    `text` is the program itself, so a replayed run reconstructs exactly the interface that
    was shown. It is redacted by the bus before it is written, like every other event.
    """

    type: Literal["ui.render"] = "ui.render"
    scope: ActivityScope
    call_id: str
    ok: bool
    text: str
    components: list[str] = Field(default_factory=list)
    statements: int = Field(default=0, ge=0)
    error: str | None = None


class TestResult(EventBase):
    """One verification command's outcome, parsed from its real output."""

    type: Literal["test.result"] = "test.result"
    scope: ActivityScope
    call_id: str
    command: str
    status: Literal["passed", "failed", "error", "timeout"]
    exit_code: int | None
    passed: int | None = Field(default=None, ge=0)
    failed: int | None = Field(default=None, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    failures: list[str] = Field(default_factory=list, max_length=10)
    summary: str = ""


class PlanCreated(EventBase):
    type: Literal["plan.created"] = "plan.created"
    plan: PlanRecord


class PlanStepUpdated(EventBase):
    type: Literal["plan.step.updated"] = "plan.step.updated"
    plan_id: str
    revision: str
    progress: StepProgress


class ActivityStarted(EventBase):
    type: Literal["activity.started"] = "activity.started"
    scope: ActivityScope
    task: str | None = None


class ActivityFinished(EventBase):
    type: Literal["activity.finished"] = "activity.finished"
    scope: ActivityScope
    status: Literal["completed", "failed", "cancelled", "interrupted"]


class SubagentStarted(EventBase):
    type: Literal["subagent.started"] = "subagent.started"
    scope: ActivityScope
    task: str
    read_only: Literal[True] = True


class SubagentFinished(EventBase):
    type: Literal["subagent.finished"] = "subagent.finished"
    scope: ActivityScope
    status: Literal["completed", "failed", "cancelled", "interrupted"]
    result: str | None = None


class ContextSummarized(EventBase):
    type: Literal["context.summarized"] = "context.summarized"
    scope: ActivityScope
    operation_id: str
    source: Literal["deepagents.summarization"] = "deepagents.summarization"
    affected_messages: int | None = Field(default=None, ge=1)


class ContextUpdated(EventBase):
    type: Literal["context.updated"] = "context.updated"
    scope: ActivityScope
    input_tokens: int = Field(ge=0)
    context_window: int | None = Field(default=None, ge=1)
    estimated: bool
    context_window_estimated: bool = False
    breakdown: ContextBreakdown | None = None


class SteeringUpdated(EventBase):
    type: Literal["steering.updated"] = "steering.updated"
    message: SteeringRecord


class ReasoningDelta(EventBase):
    type: Literal["reasoning.delta"] = "reasoning.delta"
    message_id: str
    text: str
    scope: ActivityScope | None = None


class UsageUpdated(EventBase):
    type: Literal["usage.updated"] = "usage.updated"
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated: bool


class SkillLoaded(EventBase):
    """A skill's body entered the conversation, by tool call or by slash command."""

    type: Literal["skill.loaded"] = "skill.loaded"
    name: str
    source: Literal["bundled", "user", "workspace"] = "bundled"
    command: str | None = None
    tokens: int = Field(default=0, ge=0)


class VerifyRequired(EventBase):
    """The harness blocked a finish because the changes are unverified."""

    type: Literal["verify.required"] = "verify.required"
    reason: Literal["unverified_changes", "no_command", "declined"]
    command: str | None = None
    injections: int = Field(default=0, ge=0)
    blocked: bool = True


class BudgetUpdated(EventBase):
    type: Literal["budget.updated"] = "budget.updated"
    steps: int = Field(ge=0)
    max_steps: int = Field(ge=1)
    fix_attempts: int = Field(ge=0)
    max_fix_attempts: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    max_seconds: int = Field(ge=1)


class BudgetExhausted(EventBase):
    type: Literal["budget.exhausted"] = "budget.exhausted"
    kind: Literal["steps", "time", "verify", "fix_attempts"]
    limit: int = Field(ge=0)


Event = Annotated[
    RunStarted
    | MessageDelta
    | ReasoningDelta
    | UsageUpdated
    | ToolCall
    | ToolResult
    | ApprovalRequested
    | ApprovalResolved
    | QuestionAsked
    | QuestionAnswered
    | RunFinished
    | RunError
    | PlanCreated
    | PlanStepUpdated
    | ActivityStarted
    | ActivityFinished
    | SubagentStarted
    | SubagentFinished
    | ContextSummarized
    | ContextUpdated
    | SteeringUpdated
    | TestResult
    | SkillLoaded
    | VerifyRequired
    | BudgetUpdated
    | BudgetExhausted
    | UiRender,
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
    seed_summary_from: str | None = Field(default=None, pattern=r"^[a-f0-9]{8,64}$")
    """Start from that run's summary instead of replaying its conversation."""
    schedule_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    """Set only by the scheduler, so a run can say which schedule asked for it.

    It is on the request rather than in a side table because `request.json` is the run's own
    record of what it was asked: a scheduled run that cannot name its schedule is not evidence.
    """


class RunSummary(WireModel):
    run_id: str
    summary: str
    created_at: datetime


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
    approval_resolution: ApprovalResolution
    command_result: CommandResult
    file_listing: FileListing
    revert_result: RevertResult
    snapshot_entry: SnapshotEntry
    branch_switch: BranchSwitch
    branch_switch_result: BranchSwitchResult
    branch_list: BranchList
    rules_response: RulesResponse
    rules_file: RulesFile
    question_request: QuestionRequest
    question_record: QuestionRecord
    question_decision: QuestionDecision
    steering_submission: SteeringSubmission
    planning_settings: PlanningSettings
    verify_settings: VerifySettingsResponse
    verify_config: VerifyConfig
    test_outcome: TestOutcome
    run_summary: RunSummary
    run_files: RunFileList
    skill_record: SkillRecord
    skill_detail: SkillDetail
    skill_command: SkillCommand
    skills_response: SkillsResponse
    marketplace_catalog: MarketplaceCatalog
    connector_status: ConnectorStatus
    connector_list: ConnectorList
    mcp_server_input: McpServerInput
    agent_record: AgentRecord
    agent_document: AgentDocument
    agent_write_input: AgentWriteInput
    memory_document: MemoryDocument
    customize_settings: CustomizeSettings
    data_summary: DataSummary
    deleted_runs: DeletedRuns
    app_info: AppInfo
