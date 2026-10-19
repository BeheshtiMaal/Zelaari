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
  | RunFinished
  | RunError
  | FutureEvent;
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
export type Type8 = "run.finished";
export type Status = "completed" | "stopped" | "error";
export type RunId10 = string;
export type Seq9 = number;
export type Ts9 = string;
export type Type9 = "run.error";
export type Message = string;
export type RunId11 = string;
export type Seq10 = number;
export type Ts10 = string;
export type Type10 =
  | "plan.created"
  | "plan.step.updated"
  | "subagent.started"
  | "subagent.finished"
  | "context.summarized"
  | "question.asked"
  | "question.answered"
  | "ui.render"
  | "test.result";
export type Task1 = string;
export type Workspace1 = string;
export type Model1 = string;
export type Mode = "read-only" | "ask" | "auto";
export type Worktree = boolean;
export type WorktreeApproved = boolean;
export type RunId12 = string;
export type Status1 = "ok";
export type Id = string;
export type Name1 = string;
export type BaseUrl = string;
export type Model2 = string;
export type Id1 = string;
export type Name2 = string;
export type Model3 = string;
export type Kind1 = "demo" | "openai-compatible" | "anthropic";
export type BaseUrl1 = string | null;
export type ApiKeyRef = string | null;
export type KeySuffix = string;
export type Tokens = number;
export type Source = "metadata" | "table" | "error" | "fallback";
export type Estimated1 = boolean;
export type Status2 = "untested" | "testing" | "retrying" | "ok" | "error";
export type Code = ("unauthorized" | "rate_limit" | "no_tools" | "network" | "vault") | null;
export type Attempt = number;
export type RetrySeconds = number;
export type SupportsTools = boolean;
export type Locale = "fa" | "en";
export type DefaultModel = string | null;
export type Name3 = string;
export type Url = string | null;
export type Path1 = string;
export type Name4 = string;
export type Branch = string | null;
export type Recent = Workspace2[];
export type Selected = string | null;
export type WaitingOn = ("approval" | "question")[];
export type Id2 = string;
export type Workspace3 = string;
export type Title = string;
export type Model4 = string;
export type Mode1 = "read-only" | "ask" | "auto";
export type Status3 = "running" | "completed" | "stopped" | "error" | "interrupted";
export type Worktree1 = string | null;
export type Tasks = TaskRecord[];
export type Decision1 = "approve" | "reject";
export type Reason2 = string | null;
export type EditedArgs = {
  [k: string]: JsonValue;
} | null;
export type AllowGlob = string | null;
export type Revision1 = string | null;
export type InterruptId = string;
export type Status4 = "pending" | "approved" | "rejected" | "cancelled";
export type Decision2 = "approve" | "reject";
export type Reason3 = string | null;
export type EditedArgs1 = {
  [k: string]: JsonValue;
} | null;
export type AllowGlob1 = string | null;
export type Revision2 = string | null;
export type ApprovalId2 = string;
export type ResolvedAt = string | null;
export type ExecutionStatus = "not_started" | "running" | "completed" | "interrupted";
export type Result = string | null;
export type Status5 = "ok";
export type RunId13 = string | null;
export type Command1 = string;
export type Shell = "powershell" | "cmd";
export type ExitCode = number | null;
export type DurationMs = number;
export type Output = string;
export type Truncated = boolean;
export type TotalLines = number;
export type Offset = number;
export type TimedOut = boolean;
export type TimeoutSeconds = number;
export type KilledTree = boolean;
export type Path2 = string;
export type Kind2 = "file" | "dir";
export type Name5 = string;
export type Path3 = string;
export type Kind3 = "file" | "dir";
export type Size = number;
export type Changed = boolean;
export type Entries = FileEntry[];
export type Path4 = string;
export type Text3 = string;
export type Binary = boolean;
export type Truncated1 = boolean;
export type ChangedLines = [unknown, unknown][];
export type PendingApproval = boolean;
export type Path5 = string;
export type SnapshotId = string;
export type CreatedSnapshotId = string;
export type Id3 = string;
export type Path6 = string;
export type Existed = boolean;
export type Ts11 = string;
export type RunId14 = string | null;
export type CallId2 = string | null;
export type Bytes = number;
export type Tool1 = string;
export type Workspace4 = string;
export type Branch1 = string;
export type Approved = boolean;
export type Mode2 = ("read-only" | "ask" | "auto") | null;
export type Branch2 = string | null;
export type Error = string | null;
export type Git = boolean;
export type Current = string | null;
export type Branches = string[];
export type Version = number;
export type Mode3 = "read-only" | "ask" | "auto";
export type Glob = string;
export type Action = "allow" | "ask" | "deny";
export type Mode4 = "read-only" | "ask" | "auto";
export type AlwaysAsk = string[];

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
}
export interface ReasoningDelta {
  run_id: RunId2;
  seq: Seq2;
  ts?: Ts2;
  type?: Type2;
  message_id: MessageId1;
  text: Text1;
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
export interface RunFinished {
  run_id: RunId9;
  seq: Seq8;
  ts?: Ts8;
  type?: Type8;
  status: Status;
}
export interface RunError {
  run_id: RunId10;
  seq: Seq9;
  ts?: Ts9;
  type?: Type9;
  message: Message;
}
/**
 * Reserved events: not emitted by the Phase 3 bridge.
 */
export interface FutureEvent {
  run_id: RunId11;
  seq: Seq10;
  ts?: Ts10;
  type: Type10;
  data: Data;
}
export interface Data {
  [k: string]: JsonValue;
}
export interface RunRequest {
  task: Task1;
  workspace: Workspace1;
  model?: Model1;
  mode?: Mode;
  worktree?: Worktree;
  worktree_approved?: WorktreeApproved;
}
export interface RunResponse {
  run_id: RunId12;
}
export interface HealthResponse {
  status?: Status1;
}
export interface ModelInput {
  id: Id;
  name: Name1;
  base_url: BaseUrl;
  model: Model2;
}
export interface ProviderRecord {
  id?: Id1;
  name: Name2;
  model: Model3;
  kind: Kind1;
  base_url?: BaseUrl1;
  api_key_ref?: ApiKeyRef;
  key_suffix?: KeySuffix;
  context?: Context;
  probe?: Probe;
  supports_tools?: SupportsTools;
}
export interface Context {
  tokens?: Tokens;
  source?: Source;
  estimated?: Estimated1;
}
export interface Probe {
  status?: Status2;
  code?: Code;
  attempt?: Attempt;
  retry_seconds?: RetrySeconds;
}
export interface Settings {
  locale?: Locale;
  default_model?: DefaultModel;
}
export interface Preset {
  name: Name3;
  url: Url;
}
export interface WorkspaceState {
  recent?: Recent;
  selected?: Selected;
  tasks?: Tasks;
}
export interface Workspace2 {
  path: Path1;
  name: Name4;
  branch?: Branch;
}
export interface TaskRecord {
  waiting_on?: WaitingOn;
  id: Id2;
  workspace: Workspace3;
  title: Title;
  model: Model4;
  mode?: Mode1;
  status?: Status3;
  worktree?: Worktree1;
}
export interface ApprovalDecision {
  decision: Decision1;
  reason?: Reason2;
  edited_args?: EditedArgs;
  allow_glob?: AllowGlob;
  revision?: Revision1;
}
export interface ApprovalRecord {
  request: ApprovalRequest;
  interrupt_id: InterruptId;
  status?: Status4;
  answer?: ApprovalAnswer | null;
  resolved_at?: ResolvedAt;
  execution_status?: ExecutionStatus;
  result?: Result;
}
/**
 * The resume value for one interrupt.
 *
 * `approval_id` is carried so a resumed run cannot apply a decision to the wrong
 * call if a turn ever holds more than one pending approval.
 */
export interface ApprovalAnswer {
  decision: Decision2;
  reason?: Reason3;
  edited_args?: EditedArgs1;
  allow_glob?: AllowGlob1;
  revision?: Revision2;
  approval_id: ApprovalId2;
}
export interface ApprovalResolution {
  status?: Status5;
  run_id?: RunId13;
}
/**
 * What `run_command` returns to the model and what the timeout card reads.
 */
export interface CommandResult {
  command: Command1;
  shell: Shell;
  exit_code?: ExitCode;
  duration_ms?: DurationMs;
  output?: Output;
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
  kind: Kind2;
  entries?: Entries;
  file?: FileContent | null;
}
export interface FileEntry {
  name: Name5;
  path: Path3;
  kind: Kind3;
  size?: Size;
  changed?: Changed;
}
export interface FileContent {
  path: Path4;
  text: Text3;
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
  id: Id3;
  path: Path6;
  existed: Existed;
  ts: Ts11;
  run_id?: RunId14;
  call_id?: CallId2;
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
  error?: Error;
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

export type HarnessEvent = Protocol["event"];
