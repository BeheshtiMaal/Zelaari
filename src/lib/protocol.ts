/* Generated from backend/agent/events.py. Run npm run generate:protocol. */

export type Event = RunStarted | MessageDelta | ToolCall | ToolResult | RunFinished | RunError | FutureEvent;
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
export type Type2 = "tool.call";
export type CallId = string;
export type Name = string;
export type JsonValue = unknown;
export type RunId3 = string;
export type Seq3 = number;
export type Ts3 = string;
export type Type3 = "tool.result";
export type CallId1 = string;
export type Text1 = string;
export type RunId4 = string;
export type Seq4 = number;
export type Ts4 = string;
export type Type4 = "run.finished";
export type Status = "completed" | "stopped" | "error";
export type RunId5 = string;
export type Seq5 = number;
export type Ts5 = string;
export type Type5 = "run.error";
export type Message = string;
export type RunId6 = string;
export type Seq6 = number;
export type Ts6 = string;
export type Type6 =
  | "plan.created"
  | "plan.step.updated"
  | "reasoning.delta"
  | "subagent.started"
  | "subagent.finished"
  | "context.summarized"
  | "approval.requested"
  | "approval.resolved"
  | "question.asked"
  | "question.answered"
  | "ui.render"
  | "test.result"
  | "usage.updated";
export type Task1 = string;
export type Workspace = string;
export type Model1 = "demo" | "openai-compatible";
export type RunId7 = string;
export type Status1 = "ok";

/**
 * Schema-generation envelope only; never sent over the wire.
 */
export interface Protocol {
  event: Event;
  run_request: RunRequest;
  run_response: RunResponse;
  health: HealthResponse;
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
export interface ToolCall {
  run_id: RunId2;
  seq: Seq2;
  ts?: Ts2;
  type?: Type2;
  call_id: CallId;
  name: Name;
  args: Args;
}
export interface Args {
  [k: string]: JsonValue;
}
export interface ToolResult {
  run_id: RunId3;
  seq: Seq3;
  ts?: Ts3;
  type?: Type3;
  call_id: CallId1;
  text: Text1;
}
export interface RunFinished {
  run_id: RunId4;
  seq: Seq4;
  ts?: Ts4;
  type?: Type4;
  status: Status;
}
export interface RunError {
  run_id: RunId5;
  seq: Seq5;
  ts?: Ts5;
  type?: Type5;
  message: Message;
}
/**
 * Reserved events: not emitted by the Phase 1 bridge.
 */
export interface FutureEvent {
  run_id: RunId6;
  seq: Seq6;
  ts?: Ts6;
  type: Type6;
  data: Data;
}
export interface Data {
  [k: string]: JsonValue;
}
export interface RunRequest {
  task: Task1;
  workspace: Workspace;
  model?: Model1;
}
export interface RunResponse {
  run_id: RunId7;
}
export interface HealthResponse {
  status?: Status1;
}

export type HarnessEvent = Protocol["event"];
