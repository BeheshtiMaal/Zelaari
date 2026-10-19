/* Generated from backend/agent/events.py. Run npm run generate:protocol. */

export type Event =
  | RunStarted
  | MessageDelta
  | ReasoningDelta
  | UsageUpdated
  | ToolCall
  | ToolResult
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
export type Type6 = "run.finished";
export type Status = "completed" | "stopped" | "error";
export type RunId7 = string;
export type Seq7 = number;
export type Ts7 = string;
export type Type7 = "run.error";
export type Message = string;
export type RunId8 = string;
export type Seq8 = number;
export type Ts8 = string;
export type Type8 =
  | "plan.created"
  | "plan.step.updated"
  | "subagent.started"
  | "subagent.finished"
  | "context.summarized"
  | "approval.requested"
  | "approval.resolved"
  | "question.asked"
  | "question.answered"
  | "ui.render"
  | "test.result";
export type Task1 = string;
export type Workspace = string;
export type Model1 = string;
export type Mode = "read-only" | "ask" | "auto";
export type RunId9 = string;
export type Status1 = "ok";
export type Id = string;
export type Name1 = string;
export type BaseUrl = string;
export type Model2 = string;
export type Id1 = string;
export type Name2 = string;
export type Model3 = string;
export type Kind = "demo" | "openai-compatible" | "anthropic";
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
export type Path = string;
export type Name4 = string;
export type Branch = string | null;
export type Recent = Workspace1[];
export type Selected = string | null;
export type Id2 = string;
export type Workspace2 = string;
export type Title = string;
export type Model4 = string;
export type Mode1 = "read-only" | "ask" | "auto";
export type Status3 = "running" | "completed" | "stopped" | "error" | "interrupted";
export type Tasks = TaskRecord[];

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
export interface RunFinished {
  run_id: RunId6;
  seq: Seq6;
  ts?: Ts6;
  type?: Type6;
  status: Status;
}
export interface RunError {
  run_id: RunId7;
  seq: Seq7;
  ts?: Ts7;
  type?: Type7;
  message: Message;
}
/**
 * Reserved events: not emitted by the Phase 1 bridge.
 */
export interface FutureEvent {
  run_id: RunId8;
  seq: Seq8;
  ts?: Ts8;
  type: Type8;
  data: Data;
}
export interface Data {
  [k: string]: JsonValue;
}
export interface RunRequest {
  task: Task1;
  workspace: Workspace;
  model?: Model1;
  mode?: Mode;
}
export interface RunResponse {
  run_id: RunId9;
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
  kind: Kind;
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
export interface Workspace1 {
  path: Path;
  name: Name4;
  branch?: Branch;
}
export interface TaskRecord {
  id: Id2;
  workspace: Workspace2;
  title: Title;
  model: Model4;
  mode?: Mode1;
  status?: Status3;
}

export type HarnessEvent = Protocol["event"];
