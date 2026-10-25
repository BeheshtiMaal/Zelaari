/* Generated from backend/agent/events.py. Run npm run generate:protocol. */

export type Event =
  | RunStarted
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
  | UiRender;
export type RunId = string;
export type Seq = number;
export type Ts = string;
export type Type = "run.started";
export type Task = string;
export type Model = string;
export type RunId1 = string;
export type Seq1 = number;
export type Ts1 = string;
export type Type1 = "message.delta";
export type MessageId = string;
export type Text = string;
export type ScopeId = string;
export type InvocationId = string | null;
export type StepId = string | null;
export type ParentScopeId = string | null;
export type TurnId = string | null;
export type Agent = string;
export type Model1 = string | null;
export type Provider = string | null;
export type RunId2 = string;
export type Seq2 = number;
export type Ts2 = string;
export type Type2 = "reasoning.delta";
export type MessageId1 = string;
export type Text1 = string;
export type RunId3 = string;
export type Seq3 = number;
export type Ts3 = string;
export type Type3 = "usage.updated";
export type InputTokens = number;
export type OutputTokens = number;
export type Estimated = boolean;
export type RunId4 = string;
export type Seq4 = number;
export type Ts4 = string;
export type Type4 = "tool.call";
export type CallId = string;
export type Name = string;
export type JsonValue = unknown;
export type RunId5 = string;
export type Seq5 = number;
export type Ts5 = string;
export type Type5 = "tool.result";
export type CallId1 = string;
export type Text2 = string;
export type RunId6 = string;
export type Seq6 = number;
export type Ts6 = string;
export type Type6 = "approval.requested";
export type ApprovalId = string;
export type RunId7 = string;
export type Kind = "tool" | "command";
export type Tool = string;
export type Path = string | null;
export type Command = string | null;
export type Level = "low" | "high";
export type Reasons = string[];
export type Reason = string;
export type Workspace = string;
export type SourceTitle = string;
export type SourceKind = "task" | "schedule" | "configuration";
export type AgentReason = string | null;
export type PolicyCode = string;
export type Diff = string;
export type Revision = string | null;
export type PlanId = string | null;
export type StepId1 = string | null;
export type PlanBefore = {
  [k: string]: JsonValue;
} | null;
export type PlanProposed = {
  [k: string]: JsonValue;
} | null;
export type PlanFileScope = {
  [k: string]: JsonValue;
} | null;
export type CreatedAt = string;
export type RunId8 = string;
export type Seq7 = number;
export type Ts7 = string;
export type Type7 = "approval.resolved";
export type ApprovalId1 = string;
export type Decision = "approve" | "reject";
export type Reason1 = string | null;
export type RunId9 = string;
export type Seq8 = number;
export type Ts8 = string;
export type Type8 = "question.asked";
/**
 * @minItems 1
 * @maxItems 3
 */
export type Questions = [Question] | [Question, Question] | [Question, Question, Question];
export type Id = string;
export type Header = string;
export type Text3 = string;
export type Type9 = "single" | "multi" | "rank";
/**
 * @minItems 2
 * @maxItems 4
 */
export type Options =
  | [QuestionOption, QuestionOption]
  | [QuestionOption, QuestionOption, QuestionOption]
  | [QuestionOption, QuestionOption, QuestionOption, QuestionOption];
export type Id1 = string;
export type Label = string;
export type Description = string;
export type Presentation = "standard" | "exhausted";
export type Context = string;
export type Attempts = number;
export type Step = string;
export type Check = string;
export type Output = string;
export type Kind1 = "question";
export type RunId10 = string;
export type CallId2 = string;
export type CreatedAt1 = string;
export type InterruptId = string;
export type Status = "pending" | "answered" | "declined" | "cancelled";
export type Kind2 = "question";
export type InterruptId1 = string;
export type Status1 = "answered" | "declined";
/**
 * @maxItems 3
 */
export type Answers =
  | []
  | [QuestionSelection]
  | [QuestionSelection, QuestionSelection]
  | [QuestionSelection, QuestionSelection, QuestionSelection];
export type QuestionId = string;
/**
 * @maxItems 4
 */
export type OptionIds = [] | [string] | [string, string] | [string, string, string] | [string, string, string, string];
export type Other = string | null;
export type Hint = string | null;
export type RunId11 = string;
export type CallId3 = string;
export type ResolvedAt = string | null;
export type RunId12 = string;
export type Seq9 = number;
export type Ts9 = string;
export type Type10 = "question.answered";
export type RunId13 = string;
export type Seq10 = number;
export type Ts10 = string;
export type Type11 = "run.finished";
export type Status2 = "completed" | "stopped" | "error";
export type RunId14 = string;
export type Seq11 = number;
export type Ts11 = string;
export type Type12 = "run.error";
export type Message = string;
export type RunId15 = string;
export type Seq12 = number;
export type Ts12 = string;
export type Type13 = "plan.created";
export type RunId16 = string;
export type PlanId1 = string;
export type Revision1 = string;
/**
 * @minItems 1
 * @maxItems 64
 */
export type BaselineIds = [string, ...string[]];
/**
 * @minItems 1
 * @maxItems 64
 */
export type Steps = [PlanStep, ...PlanStep[]];
export type Id2 = string;
export type Title = string;
/**
 * @maxItems 64
 */
export type ExpectedFiles = string[];
export type VerifyCommand = string | null;
export type HighRisk = boolean;
/**
 * @minItems 1
 * @maxItems 64
 */
export type Progress = [StepProgress, ...StepProgress[]];
export type StepId2 = string;
export type Status3 = "pending" | "in_progress" | "completed" | "failed";
export type StartedAt = string | null;
export type EndedAt = string | null;
export type Adoption = "pending" | "automatic" | "approved" | "rejected";
/**
 * @maxItems 16
 */
export type GateReasons =
  | []
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string, string, string]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ];
/**
 * @maxItems 10000
 */
export type KnownFiles = string[];
export type Uncertain = boolean;
export type Revision2 = string;
export type StepThreshold = number;
export type FileThreshold = number;
export type DeviationGate = boolean;
export type RunId17 = string;
export type Seq13 = number;
export type Ts13 = string;
export type Type14 = "plan.step.updated";
export type PlanId2 = string;
export type Revision3 = string;
export type RunId18 = string;
export type Seq14 = number;
export type Ts14 = string;
export type Type15 = "activity.started";
export type Task1 = string | null;
export type RunId19 = string;
export type Seq15 = number;
export type Ts15 = string;
export type Type16 = "activity.finished";
export type Status4 = "completed" | "failed" | "cancelled" | "interrupted";
export type RunId20 = string;
export type Seq16 = number;
export type Ts16 = string;
export type Type17 = "subagent.started";
export type Task2 = string;
export type ReadOnly = true;
export type RunId21 = string;
export type Seq17 = number;
export type Ts17 = string;
export type Type18 = "subagent.finished";
export type Status5 = "completed" | "failed" | "cancelled" | "interrupted";
export type Result = string | null;
export type RunId22 = string;
export type Seq18 = number;
export type Ts18 = string;
export type Type19 = "context.summarized";
export type OperationId = string;
export type Source = "deepagents.summarization";
export type AffectedMessages = number | null;
export type RunId23 = string;
export type Seq19 = number;
export type Ts19 = string;
export type Type20 = "context.updated";
export type InputTokens1 = number;
export type ContextWindow = number | null;
export type Estimated1 = boolean;
export type ContextWindowEstimated = boolean;
export type Messages = number;
export type ToolResults = number;
export type System = number;
export type Skills = number;
export type Memory = number;
export type Estimated2 = boolean;
export type RunId24 = string;
export type Seq20 = number;
export type Ts20 = string;
export type Type21 = "steering.updated";
export type SubmissionId = string;
export type Text4 = string;
export type RunId25 = string;
export type Ordinal = number;
export type Status6 = "queued" | "delivered" | "cancelled";
export type QueuedAt = string;
export type DeliveredAt = string | null;
export type RunId26 = string;
export type Seq21 = number;
export type Ts21 = string;
export type Type22 = "test.result";
export type CallId4 = string;
export type Command1 = string;
export type Status7 = "passed" | "failed" | "error" | "timeout";
export type ExitCode = number | null;
export type Passed = number | null;
export type Failed = number | null;
export type DurationMs = number;
/**
 * @maxItems 10
 */
export type Failures =
  | []
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string];
export type Summary = string;
export type RunId27 = string;
export type Seq22 = number;
export type Ts22 = string;
export type Type23 = "skill.loaded";
export type Name1 = string;
export type Source1 = "bundled" | "user" | "workspace";
export type Command2 = string | null;
export type Tokens = number;
export type RunId28 = string;
export type Seq23 = number;
export type Ts23 = string;
export type Type24 = "verify.required";
export type Reason2 = "unverified_changes" | "no_command" | "declined";
export type Command3 = string | null;
export type Injections = number;
export type Blocked = boolean;
export type RunId29 = string;
export type Seq24 = number;
export type Ts24 = string;
export type Type25 = "budget.updated";
export type Steps1 = number;
export type MaxSteps = number;
export type FixAttempts = number;
export type MaxFixAttempts = number;
export type ElapsedMs = number;
export type MaxSeconds = number;
export type RunId30 = string;
export type Seq25 = number;
export type Ts25 = string;
export type Type26 = "budget.exhausted";
export type Kind3 = "steps" | "time" | "verify" | "fix_attempts";
export type Limit = number;
export type RunId31 = string;
export type Seq26 = number;
export type Ts26 = string;
export type Type27 = "ui.render";
export type CallId5 = string;
export type Ok = boolean;
export type Text5 = string;
export type Components = string[];
export type Statements = number;
export type Error = string | null;
export type Task3 = string;
export type Workspace1 = string;
export type Model2 = string;
export type Mode = "read-only" | "ask" | "auto";
export type Worktree = boolean;
export type WorktreeApproved = boolean;
export type SeedSummaryFrom = string | null;
export type RunId32 = string;
export type Status8 = "ok";
export type Id3 = string;
export type Name2 = string;
export type BaseUrl = string;
export type Model3 = string;
export type Id4 = string;
export type Name3 = string;
export type Model4 = string;
export type Kind4 = "demo" | "openai-compatible" | "anthropic";
export type BaseUrl1 = string | null;
export type ApiKeyRef = string | null;
export type KeySuffix = string;
export type Tokens1 = number;
export type Source2 = "metadata" | "table" | "error" | "fallback";
export type Estimated3 = boolean;
export type Status9 = "untested" | "testing" | "retrying" | "ok" | "error";
export type Code = ("unauthorized" | "rate_limit" | "no_tools" | "network" | "vault") | null;
export type Attempt = number;
export type RetrySeconds = number;
export type SupportsTools = boolean;
export type Locale = "fa" | "en";
export type DefaultModel = string | null;
export type Name4 = string;
export type Url = string | null;
export type Path1 = string;
export type Name5 = string;
export type Branch = string | null;
export type Recent = Workspace2[];
export type Selected = string | null;
export type WaitingOn = ("approval" | "question")[];
export type Id5 = string;
export type Workspace3 = string;
export type Title1 = string;
export type Model5 = string;
export type Mode1 = "read-only" | "ask" | "auto";
export type Status10 = "running" | "completed" | "stopped" | "error" | "interrupted";
export type Worktree1 = string | null;
export type Tasks = TaskRecord[];
export type Decision1 = "approve" | "reject";
export type Reason3 = string | null;
export type EditedArgs = {
  [k: string]: JsonValue;
} | null;
export type AllowGlob = string | null;
export type Revision4 = string | null;
export type InterruptId2 = string;
export type Status11 = "pending" | "approved" | "rejected" | "cancelled";
export type Decision2 = "approve" | "reject";
export type Reason4 = string | null;
export type EditedArgs1 = {
  [k: string]: JsonValue;
} | null;
export type AllowGlob1 = string | null;
export type Revision5 = string | null;
export type ApprovalId2 = string;
export type ResolvedAt1 = string | null;
export type ExecutionStatus = "not_started" | "running" | "completed" | "interrupted";
export type Result1 = string | null;
export type Status12 = "ok";
export type RunId33 = string | null;
export type Command4 = string;
export type Shell = "powershell" | "cmd";
export type ExitCode1 = number | null;
export type DurationMs1 = number;
export type Output1 = string;
export type Truncated = boolean;
export type TotalLines = number;
export type Offset = number;
export type TimedOut = boolean;
export type TimeoutSeconds = number;
export type KilledTree = boolean;
export type Path2 = string;
export type Kind5 = "file" | "dir";
export type Name6 = string;
export type Path3 = string;
export type Kind6 = "file" | "dir";
export type Size = number;
export type Changed = boolean;
export type Entries = FileEntry[];
export type Path4 = string;
export type Text6 = string;
export type Binary = boolean;
export type Truncated1 = boolean;
export type ChangedLines = [unknown, unknown][];
export type PendingApproval = boolean;
export type Path5 = string;
export type SnapshotId = string;
export type CreatedSnapshotId = string;
export type Id6 = string;
export type Path6 = string;
export type Existed = boolean;
export type Ts27 = string;
export type RunId34 = string | null;
export type CallId6 = string | null;
export type Bytes = number;
export type Tool1 = string;
export type Workspace4 = string;
export type Branch1 = string;
export type Approved = boolean;
export type Mode2 = ("read-only" | "ask" | "auto") | null;
export type Branch2 = string | null;
export type Error1 = string | null;
export type Git = boolean;
export type Current = string | null;
export type Branches = string[];
export type Version = number;
export type Mode3 = "read-only" | "ask" | "auto";
export type Glob = string;
export type Action = "allow" | "ask" | "deny";
export type Mode4 = "read-only" | "ask" | "auto";
export type AlwaysAsk = string[];
export type Kind7 = "question";
export type InterruptId3 = string;
export type Status13 = "answered" | "declined";
/**
 * @maxItems 3
 */
export type Answers1 =
  | []
  | [QuestionSelection]
  | [QuestionSelection, QuestionSelection]
  | [QuestionSelection, QuestionSelection, QuestionSelection];
export type SubmissionId1 = string;
export type Text7 = string;
export type CompactionPercent = number;
export type KeepMessages = number;
export type Offload = boolean;
export type ShowRing = boolean;
export type Gate = boolean;
export type Command5 = string | null;
export type MaxSteps1 = number;
export type MaxMinutes = number;
export type FixAttempts1 = number;
export type Shell1 = string;
export type TimeoutSeconds1 = number;
export type MaxOutputLines = number;
export type Command6 = string | null;
export type Source3 = "custom" | "pytest.ini" | "pyproject.toml" | "tests" | "package.json" | "none";
export type Status14 = "passed" | "failed" | "error" | "timeout";
export type ExitCode2 = number | null;
export type Passed1 = number | null;
export type Failed1 = number | null;
export type DurationMs2 = number;
/**
 * @maxItems 10
 */
export type Failures1 =
  | []
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string];
export type Summary1 = string;
export type RunId35 = string;
export type Summary2 = string;
export type CreatedAt2 = string;
export type RunId36 = string;
export type Path7 = string;
export type Tool2 = string;
export type Created = boolean;
export type Ts28 = string;
export type Files = RunFile[];
export type Name7 = string;
export type Description1 = string;
export type Command7 = string | null;
export type Category = "coding" | "tests" | "web" | "docs" | "other";
export type Source4 = "bundled" | "user" | "workspace";
export type Path8 = string;
export type Enabled = boolean;
export type RequiresApproval = boolean;
export type Tokens2 = number;
export type Status15 = "clean" | "flagged" | "blocked";
export type Findings = string[];
export type Scripts = string[];
export type Problem = string | null;
export type Name8 = string;
export type Description2 = string;
export type Command8 = string | null;
export type Category1 = "coding" | "tests" | "web" | "docs" | "other";
export type Source5 = "bundled" | "user" | "workspace";
export type Path9 = string;
export type Enabled1 = boolean;
export type RequiresApproval1 = boolean;
export type Tokens3 = number;
export type Problem1 = string | null;
export type Body = string;
export type References = string[];
export type Command9 = string;
export type Name9 = string;
export type Description3 = string;
export type RequiresApproval2 = boolean;
export type Workspace5 = string;
export type Skills1 = SkillRecord[];
export type Commands = SkillCommand[];
export type CatalogUrl = string | null;
export type FetchedAt = string | null;
export type Problems = SkillRecord[];
export type Version1 = 1;
export type Name10 = string;
export type Description4 = string;
export type Url1 = string;
export type Command10 = string | null;
export type Category2 = "coding" | "tests" | "web" | "docs" | "other";
export type Version2 = string | null;
export type Author = string | null;
export type Skills2 = MarketplaceEntry[];
export type FetchedAt1 = string | null;
export type CatalogUrl1 = string | null;
export type Error2 = string | null;
export type Name11 = string;
export type Transport = "stdio" | "http";
export type Display = string;
export type Enabled2 = boolean;
export type Status16 = "connected" | "error" | "disabled";
export type Name12 = string;
export type Namespaced = string;
export type Description5 = string;
export type InputSchema = string;
export type Tools2 = McpTool[];
export type Error3 = string | null;
export type Workspace6 = string;
export type Servers = ConnectorStatus[];
export type Name13 = string;
export type Transport1 = "stdio" | "http";
export type Command11 = string | null;
export type Url2 = string | null;
export type EnvKeys = string[];
export type Enabled3 = boolean;
export type Name14 = string;
export type Description6 = string;
export type Source6 = "workspace";
export type Tools3 = string[];
export type Path10 = string;
export type Problem2 = string | null;
export type Instructions = string;
export type Name15 = string;
export type Description7 = string;
export type Instructions1 = string;
export type Tools4 = string[];
export type Workspace7 = string;
export type Content = string;
export type Bytes1 = number;
export type Limit1 = number;
export type Workspace8 = string;
export type Skills3 = number;
export type EnabledSkills = number;
export type Agents = number;
export type Servers1 = number;
export type MemoryBytes = number;

/**
 * Schema-generation envelope only; never sent over the wire.
 */
export interface Protocol {
  event: Event;
  run_request: RunRequest;
  run_response: RunResponse;
  health: HealthResponse;
  model_input: ModelInput;
  provider: ProviderRecord;
  settings: Settings;
  preset: Preset;
  workspaces: WorkspaceState;
  approval_request: ApprovalRequest;
  approval_decision: ApprovalDecision;
  approval_record: ApprovalRecord;
  approval_resolution: ApprovalResolution;
  command_result: CommandResult;
  file_listing: FileListing;
  revert_result: RevertResult;
  snapshot_entry: SnapshotEntry;
  branch_switch: BranchSwitch;
  branch_switch_result: BranchSwitchResult;
  branch_list: BranchList;
  rules_response: RulesResponse;
  rules_file: RulesFile;
  question_request: QuestionRequest;
  question_record: QuestionRecord;
  question_decision: QuestionDecision;
  steering_submission: SteeringSubmission;
  planning_settings: PlanningSettings;
  verify_settings: VerifySettingsResponse;
  verify_config: VerifyConfig;
  test_outcome: TestOutcome;
  run_summary: RunSummary;
  run_files: RunFileList;
  skill_record: SkillRecord;
  skill_detail: SkillDetail;
  skill_command: SkillCommand;
  skills_response: SkillsResponse;
  marketplace_catalog: MarketplaceCatalog;
  connector_status: ConnectorStatus;
  connector_list: ConnectorList;
  mcp_server_input: McpServerInput;
  agent_record: AgentRecord;
  agent_document: AgentDocument;
  agent_write_input: AgentWriteInput;
  memory_document: MemoryDocument;
  customize_settings: CustomizeSettings;
}
export interface RunStarted {
  run_id: RunId;
  seq: Seq;
  ts?: Ts;
  type?: Type;
  task: Task;
  model: Model;
}
export interface MessageDelta {
  run_id: RunId1;
  seq: Seq1;
  ts?: Ts1;
  type?: Type1;
  message_id: MessageId;
  text: Text;
  scope?: ActivityScope | null;
}
export interface ActivityScope {
  scope_id: ScopeId;
  invocation_id?: InvocationId;
  step_id?: StepId;
  parent_scope_id?: ParentScopeId;
  turn_id?: TurnId;
  agent?: Agent;
  model?: Model1;
  provider?: Provider;
}
export interface ReasoningDelta {
  run_id: RunId2;
  seq: Seq2;
  ts?: Ts2;
  type?: Type2;
  message_id: MessageId1;
  text: Text1;
  scope?: ActivityScope | null;
}
export interface UsageUpdated {
  run_id: RunId3;
  seq: Seq3;
  ts?: Ts3;
  type?: Type3;
  input_tokens: InputTokens;
  output_tokens: OutputTokens;
  estimated: Estimated;
}
export interface ToolCall {
  run_id: RunId4;
  seq: Seq4;
  ts?: Ts4;
  type?: Type4;
  call_id: CallId;
  name: Name;
  args: Args;
  scope?: ActivityScope | null;
}
export interface Args {
  [k: string]: JsonValue;
}
export interface ToolResult {
  run_id: RunId5;
  seq: Seq5;
  ts?: Ts5;
  type?: Type5;
  call_id: CallId1;
  text: Text2;
  scope?: ActivityScope | null;
}
/**
 * One tool call needs a human decision before it runs.
 */
export interface ApprovalRequested {
  run_id: RunId6;
  seq: Seq6;
  ts?: Ts6;
  type?: Type6;
  approval: ApprovalRequest;
}
/**
 * Payload of `approval.requested`.
 *
 * `approval_id` is the tool call id, so it stays stable across a resume.
 */
export interface ApprovalRequest {
  approval_id: ApprovalId;
  run_id: RunId7;
  kind: Kind;
  tool: Tool;
  path?: Path;
  command?: Command;
  risk?: RiskAssessment;
  reason?: Reason;
  args?: Args1;
  workspace?: Workspace;
  source_title?: SourceTitle;
  source_kind?: SourceKind;
  agent_reason?: AgentReason;
  policy_code?: PolicyCode;
  diff?: Diff;
  revision?: Revision;
  plan_id?: PlanId;
  step_id?: StepId1;
  plan_before?: PlanBefore;
  plan_proposed?: PlanProposed;
  plan_file_scope?: PlanFileScope;
  created_at?: CreatedAt;
}
export interface RiskAssessment {
  level?: Level;
  reasons?: Reasons;
}
export interface Args1 {
  [k: string]: JsonValue;
}
export interface ApprovalResolved {
  run_id: RunId8;
  seq: Seq7;
  ts?: Ts7;
  type?: Type7;
  approval_id: ApprovalId1;
  decision: Decision;
  reason?: Reason1;
}
export interface QuestionAsked {
  run_id: RunId9;
  seq: Seq8;
  ts?: Ts8;
  type?: Type8;
  question: QuestionRecord;
}
export interface QuestionRecord {
  request: QuestionRequest;
  interrupt_id: InterruptId;
  status?: Status;
  answer?: QuestionAnswer | null;
  resolved_at?: ResolvedAt;
}
export interface QuestionRequest {
  questions: Questions;
  presentation?: Presentation;
  context?: Context;
  failure?: FailureContext | null;
  kind?: Kind1;
  run_id: RunId10;
  call_id: CallId2;
  created_at?: CreatedAt1;
}
export interface Question {
  id: Id;
  header: Header;
  text: Text3;
  type?: Type9;
  options: Options;
}
export interface QuestionOption {
  id: Id1;
  label: Label;
  description: Description;
}
export interface FailureContext {
  attempts: Attempts;
  step: Step;
  check: Check;
  output: Output;
}
export interface QuestionAnswer {
  kind?: Kind2;
  interrupt_id: InterruptId1;
  status: Status1;
  answers?: Answers;
  run_id: RunId11;
  call_id: CallId3;
}
export interface QuestionSelection {
  question_id: QuestionId;
  option_ids?: OptionIds;
  other?: Other;
  hint?: Hint;
}
export interface QuestionAnswered {
  run_id: RunId12;
  seq: Seq9;
  ts?: Ts9;
  type?: Type10;
  answer: QuestionAnswer;
}
export interface RunFinished {
  run_id: RunId13;
  seq: Seq10;
  ts?: Ts10;
  type?: Type11;
  status: Status2;
}
export interface RunError {
  run_id: RunId14;
  seq: Seq11;
  ts?: Ts11;
  type?: Type12;
  message: Message;
}
export interface PlanCreated {
  run_id: RunId15;
  seq: Seq12;
  ts?: Ts12;
  type?: Type13;
  plan: PlanRecord;
}
export interface PlanRecord {
  run_id: RunId16;
  plan_id: PlanId1;
  revision: Revision1;
  baseline_ids: BaselineIds;
  submission: PlanSubmission;
  progress: Progress;
  adoption: Adoption;
  gate_reasons?: GateReasons;
  file_scope: FileScope;
  settings: PlanningSettings;
}
export interface PlanSubmission {
  steps: Steps;
}
export interface PlanStep {
  id: Id2;
  title: Title;
  expected_files?: ExpectedFiles;
  verify_command?: VerifyCommand;
  high_risk?: HighRisk;
}
export interface StepProgress {
  step_id: StepId2;
  status?: Status3;
  started_at?: StartedAt;
  ended_at?: EndedAt;
}
export interface FileScope {
  known_files?: KnownFiles;
  uncertain?: Uncertain;
  revision: Revision2;
}
export interface PlanningSettings {
  step_threshold?: StepThreshold;
  file_threshold?: FileThreshold;
  deviation_gate?: DeviationGate;
}
export interface PlanStepUpdated {
  run_id: RunId17;
  seq: Seq13;
  ts?: Ts13;
  type?: Type14;
  plan_id: PlanId2;
  revision: Revision3;
  progress: StepProgress;
}
export interface ActivityStarted {
  run_id: RunId18;
  seq: Seq14;
  ts?: Ts14;
  type?: Type15;
  scope: ActivityScope;
  task?: Task1;
}
export interface ActivityFinished {
  run_id: RunId19;
  seq: Seq15;
  ts?: Ts15;
  type?: Type16;
  scope: ActivityScope;
  status: Status4;
}
export interface SubagentStarted {
  run_id: RunId20;
  seq: Seq16;
  ts?: Ts16;
  type?: Type17;
  scope: ActivityScope;
  task: Task2;
  read_only?: ReadOnly;
}
export interface SubagentFinished {
  run_id: RunId21;
  seq: Seq17;
  ts?: Ts17;
  type?: Type18;
  scope: ActivityScope;
  status: Status5;
  result?: Result;
}
export interface ContextSummarized {
  run_id: RunId22;
  seq: Seq18;
  ts?: Ts18;
  type?: Type19;
  scope: ActivityScope;
  operation_id: OperationId;
  source?: Source;
  affected_messages?: AffectedMessages;
}
export interface ContextUpdated {
  run_id: RunId23;
  seq: Seq19;
  ts?: Ts19;
  type?: Type20;
  scope: ActivityScope;
  input_tokens: InputTokens1;
  context_window?: ContextWindow;
  estimated: Estimated1;
  context_window_estimated?: ContextWindowEstimated;
  breakdown?: ContextBreakdown | null;
}
export interface ContextBreakdown {
  messages: Messages;
  tool_results: ToolResults;
  system: System;
  skills: Skills;
  memory: Memory;
  estimated?: Estimated2;
}
export interface SteeringUpdated {
  run_id: RunId24;
  seq: Seq20;
  ts?: Ts20;
  type?: Type21;
  message: SteeringRecord;
}
export interface SteeringRecord {
  submission_id: SubmissionId;
  text: Text4;
  run_id: RunId25;
  ordinal: Ordinal;
  status?: Status6;
  queued_at: QueuedAt;
  delivered_at?: DeliveredAt;
}
/**
 * One verification command's outcome, parsed from its real output.
 */
export interface TestResult {
  run_id: RunId26;
  seq: Seq21;
  ts?: Ts21;
  type?: Type22;
  scope: ActivityScope;
  call_id: CallId4;
  command: Command1;
  status: Status7;
  exit_code: ExitCode;
  passed?: Passed;
  failed?: Failed;
  duration_ms?: DurationMs;
  failures?: Failures;
  summary?: Summary;
}
/**
 * A skill's body entered the conversation, by tool call or by slash command.
 */
export interface SkillLoaded {
  run_id: RunId27;
  seq: Seq22;
  ts?: Ts22;
  type?: Type23;
  name: Name1;
  source?: Source1;
  command?: Command2;
  tokens?: Tokens;
}
/**
 * The harness blocked a finish because the changes are unverified.
 */
export interface VerifyRequired {
  run_id: RunId28;
  seq: Seq23;
  ts?: Ts23;
  type?: Type24;
  reason: Reason2;
  command?: Command3;
  injections?: Injections;
  blocked?: Blocked;
}
export interface BudgetUpdated {
  run_id: RunId29;
  seq: Seq24;
  ts?: Ts24;
  type?: Type25;
  steps: Steps1;
  max_steps: MaxSteps;
  fix_attempts: FixAttempts;
  max_fix_attempts: MaxFixAttempts;
  elapsed_ms: ElapsedMs;
  max_seconds: MaxSeconds;
}
export interface BudgetExhausted {
  run_id: RunId30;
  seq: Seq25;
  ts?: Ts25;
  type?: Type26;
  kind: Kind3;
  limit: Limit;
}
/**
 * One rendering attempt: the program, whether it rendered, and why it did not.
 *
 * `text` is the program itself, so a replayed run reconstructs exactly the interface that
 * was shown. It is redacted by the bus before it is written, like every other event.
 */
export interface UiRender {
  run_id: RunId31;
  seq: Seq26;
  ts?: Ts26;
  type?: Type27;
  scope: ActivityScope;
  call_id: CallId5;
  ok: Ok;
  text: Text5;
  components?: Components;
  statements?: Statements;
  error?: Error;
}
export interface RunRequest {
  task: Task3;
  workspace: Workspace1;
  model?: Model2;
  mode?: Mode;
  worktree?: Worktree;
  worktree_approved?: WorktreeApproved;
  seed_summary_from?: SeedSummaryFrom;
}
export interface RunResponse {
  run_id: RunId32;
}
export interface HealthResponse {
  status?: Status8;
}
export interface ModelInput {
  id: Id3;
  name: Name2;
  base_url: BaseUrl;
  model: Model3;
}
export interface ProviderRecord {
  id?: Id4;
  name: Name3;
  model: Model4;
  kind: Kind4;
  base_url?: BaseUrl1;
  api_key_ref?: ApiKeyRef;
  key_suffix?: KeySuffix;
  context?: Context1;
  probe?: Probe;
  supports_tools?: SupportsTools;
}
export interface Context1 {
  tokens?: Tokens1;
  source?: Source2;
  estimated?: Estimated3;
}
export interface Probe {
  status?: Status9;
  code?: Code;
  attempt?: Attempt;
  retry_seconds?: RetrySeconds;
}
export interface Settings {
  locale?: Locale;
  default_model?: DefaultModel;
}
export interface Preset {
  name: Name4;
  url: Url;
}
export interface WorkspaceState {
  recent?: Recent;
  selected?: Selected;
  tasks?: Tasks;
}
export interface Workspace2 {
  path: Path1;
  name: Name5;
  branch?: Branch;
}
export interface TaskRecord {
  waiting_on?: WaitingOn;
  id: Id5;
  workspace: Workspace3;
  title: Title1;
  model: Model5;
  mode?: Mode1;
  status?: Status10;
  worktree?: Worktree1;
}
export interface ApprovalDecision {
  decision: Decision1;
  reason?: Reason3;
  edited_args?: EditedArgs;
  allow_glob?: AllowGlob;
  revision?: Revision4;
}
export interface ApprovalRecord {
  request: ApprovalRequest;
  interrupt_id: InterruptId2;
  status?: Status11;
  answer?: ApprovalAnswer | null;
  resolved_at?: ResolvedAt1;
  execution_status?: ExecutionStatus;
  result?: Result1;
}
/**
 * The resume value for one interrupt.
 *
 * `approval_id` is carried so a resumed run cannot apply a decision to the wrong
 * call if a turn ever holds more than one pending approval.
 */
export interface ApprovalAnswer {
  decision: Decision2;
  reason?: Reason4;
  edited_args?: EditedArgs1;
  allow_glob?: AllowGlob1;
  revision?: Revision5;
  approval_id: ApprovalId2;
}
export interface ApprovalResolution {
  status?: Status12;
  run_id?: RunId33;
}
/**
 * What `run_command` returns to the model and what the timeout card reads.
 */
export interface CommandResult {
  command: Command4;
  shell: Shell;
  exit_code?: ExitCode1;
  duration_ms?: DurationMs1;
  output?: Output1;
  truncated?: Truncated;
  total_lines?: TotalLines;
  offset?: Offset;
  timed_out?: TimedOut;
  timeout_seconds?: TimeoutSeconds;
  killed_tree?: KilledTree;
}
/**
 * `GET /files?path=` returns a directory listing or a file, never both.
 */
export interface FileListing {
  path: Path2;
  kind: Kind5;
  entries?: Entries;
  file?: FileContent | null;
}
export interface FileEntry {
  name: Name6;
  path: Path3;
  kind: Kind6;
  size?: Size;
  changed?: Changed;
}
export interface FileContent {
  path: Path4;
  text: Text6;
  binary?: Binary;
  truncated?: Truncated1;
  changed_lines?: ChangedLines;
  pending_approval?: PendingApproval;
}
export interface RevertResult {
  path: Path5;
  snapshot_id: SnapshotId;
  created_snapshot_id: CreatedSnapshotId;
}
export interface SnapshotEntry {
  id: Id6;
  path: Path6;
  existed: Existed;
  ts: Ts27;
  run_id?: RunId34;
  call_id?: CallId6;
  bytes?: Bytes;
  tool?: Tool1;
}
export interface BranchSwitch {
  workspace: Workspace4;
  branch: Branch1;
  approved?: Approved;
  mode?: Mode2;
}
export interface BranchSwitchResult {
  branch?: Branch2;
  error?: Error1;
}
/**
 * What the branch chip and the Worktree checkbox need to know before a run.
 */
export interface BranchList {
  git?: Git;
  current?: Current;
  branches?: Branches;
}
export interface RulesResponse {
  rules?: RulesFile;
  mode: Mode4;
  tools?: Tools1;
  defaults?: Defaults;
  always_ask?: AlwaysAsk;
}
/**
 * `.harness/rules.json`. Unknown keys are rejected so a typo cannot silently disable a rule.
 */
export interface RulesFile {
  version?: Version;
  mode?: Mode3;
  tools?: Tools;
}
export interface Tools {
  [k: string]: Rule[];
}
/**
 * One row of the rules grid: a path glob (or `*` for whole-tool) mapped to an action.
 */
export interface Rule {
  glob?: Glob;
  action: Action;
}
export interface Tools1 {
  [k: string]: {
    [k: string]: string;
  }[];
}
export interface Defaults {
  [k: string]: string;
}
export interface QuestionDecision {
  kind?: Kind7;
  interrupt_id: InterruptId3;
  status: Status13;
  answers?: Answers1;
}
export interface SteeringSubmission {
  submission_id: SubmissionId1;
  text: Text7;
}
export interface VerifySettingsResponse {
  context?: ContextSettings;
  verify?: VerifySettings;
  terminal?: TerminalSettings;
  detection?: Detection;
}
export interface ContextSettings {
  compaction_percent?: CompactionPercent;
  keep_messages?: KeepMessages;
  offload?: Offload;
  show_ring?: ShowRing;
}
export interface VerifySettings {
  gate?: Gate;
  command?: Command5;
  max_steps?: MaxSteps1;
  max_minutes?: MaxMinutes;
  fix_attempts?: FixAttempts1;
}
export interface TerminalSettings {
  shell?: Shell1;
  timeout_seconds?: TimeoutSeconds1;
  max_output_lines?: MaxOutputLines;
}
export interface Detection {
  command?: Command6;
  source?: Source3;
}
export interface VerifyConfig {
  context?: ContextSettings;
  verify?: VerifySettings;
  terminal?: TerminalSettings;
}
export interface TestOutcome {
  status: Status14;
  exit_code: ExitCode2;
  passed?: Passed1;
  failed?: Failed1;
  duration_ms?: DurationMs2;
  failures?: Failures1;
  summary?: Summary1;
}
export interface RunSummary {
  run_id: RunId35;
  summary: Summary2;
  created_at: CreatedAt2;
}
export interface RunFileList {
  run_id: RunId36;
  files?: Files;
}
/**
 * One path a run changed, derived from its snapshots rather than from the model's words.
 */
export interface RunFile {
  path: Path7;
  tool?: Tool2;
  created?: Created;
  ts: Ts28;
}
export interface SkillRecord {
  name: Name7;
  description: Description1;
  command?: Command7;
  category?: Category;
  source?: Source4;
  path?: Path8;
  enabled?: Enabled;
  requires_approval?: RequiresApproval;
  tokens?: Tokens2;
  scan?: SkillScan;
  problem?: Problem;
}
/**
 * What the pre-use scan found. `blocked` never reaches a model.
 */
export interface SkillScan {
  status?: Status15;
  findings?: Findings;
  scripts?: Scripts;
}
export interface SkillDetail {
  name: Name8;
  description: Description2;
  command?: Command8;
  category?: Category1;
  source?: Source5;
  path?: Path9;
  enabled?: Enabled1;
  requires_approval?: RequiresApproval1;
  tokens?: Tokens3;
  scan?: SkillScan;
  problem?: Problem1;
  body?: Body;
  references?: References;
}
export interface SkillCommand {
  command: Command9;
  name: Name9;
  description: Description3;
  requires_approval?: RequiresApproval2;
}
export interface SkillsResponse {
  workspace: Workspace5;
  skills?: Skills1;
  commands?: Commands;
  catalog_url?: CatalogUrl;
  fetched_at?: FetchedAt;
  problems?: Problems;
}
export interface MarketplaceCatalog {
  version?: Version1;
  skills?: Skills2;
  fetched_at?: FetchedAt1;
  catalog_url?: CatalogUrl1;
  error?: Error2;
}
export interface MarketplaceEntry {
  name: Name10;
  description: Description4;
  url: Url1;
  command?: Command10;
  category?: Category2;
  version?: Version2;
  author?: Author;
}
export interface ConnectorStatus {
  name: Name11;
  transport?: Transport;
  display?: Display;
  enabled?: Enabled2;
  status?: Status16;
  tools?: Tools2;
  error?: Error3;
}
export interface McpTool {
  name: Name12;
  namespaced: Namespaced;
  description?: Description5;
  input_schema?: InputSchema;
}
export interface ConnectorList {
  workspace: Workspace6;
  servers?: Servers;
}
export interface McpServerInput {
  name: Name13;
  transport?: Transport1;
  command?: Command11;
  url?: Url2;
  env_keys?: EnvKeys;
  enabled?: Enabled3;
}
export interface AgentRecord {
  name: Name14;
  description: Description6;
  source?: Source6;
  tools?: Tools3;
  path?: Path10;
  problem?: Problem2;
}
export interface AgentDocument {
  record: AgentRecord;
  instructions?: Instructions;
}
export interface AgentWriteInput {
  name: Name15;
  description: Description7;
  instructions?: Instructions1;
  tools?: Tools4;
}
export interface MemoryDocument {
  workspace: Workspace7;
  content?: Content;
  bytes?: Bytes1;
  limit?: Limit1;
}
/**
 * The hub's read-only overview: counts and the workspace it describes.
 */
export interface CustomizeSettings {
  workspace: Workspace8;
  skills?: Skills3;
  enabled_skills?: EnabledSkills;
  agents?: Agents;
  servers?: Servers1;
  memory_bytes?: MemoryBytes;
}

// Serialized events always include the Pydantic discriminator and timestamp defaults.
type WireEvent<E> = E extends { type?: infer K } ? E & { type: K } : never;
export type HarnessEvent = WireEvent<Protocol["event"]>;
