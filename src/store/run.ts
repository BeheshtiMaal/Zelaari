import { create } from "zustand";
import type { ApprovalRequest, HarnessEvent, QuestionRecord } from "../lib/protocol";

export type TimelineItem = { kind: "message"; id: string; text: string } |
  { kind: "tool"; id: string; name: string; args: Record<string, unknown>; result?: string };
export interface RunState {
  runId: string | null;
  seq: number;
  task: string;
  status: "idle" | "running" | "completed" | "stopped" | "error";
  items: TimelineItem[];
  error: string | null;
  reasoning: Record<string, string>;
  approval: ApprovalRequest | null;
  approvals: Record<string, ApprovalRequest>;
  questions: Record<string, QuestionRecord>;
  usage: { input: number; output: number; estimated: boolean };
}
export const initialRun: RunState = { runId: null, seq: 0, task: "", status: "idle", items: [], error: null, reasoning: {}, approval: null, approvals: {}, questions: {}, usage: { input: 0, output: 0, estimated: false } };

export function reduceEvent(state: RunState, event: HarnessEvent): RunState {
  if (event.type === "run.started" && event.run_id !== state.runId) {
    return { ...initialRun, runId: event.run_id, seq: event.seq, task: event.task, status: "running" };
  }
  if (event.run_id !== state.runId || event.seq <= state.seq) return state;
  const next = { ...state, seq: event.seq };
  switch (event.type) {
    case "question.asked": next.questions = { ...state.questions, [event.question.request.call_id]: event.question }; break;
    case "question.answered": {
      const record = state.questions[event.answer.call_id];
      if (record) next.questions = { ...state.questions, [event.answer.call_id]: { ...record, answer: event.answer, status: event.answer.status, resolved_at: event.ts } };
      break;
    }
    case "reasoning.delta": next.reasoning = { ...state.reasoning, [event.message_id]: (state.reasoning[event.message_id] ?? "") + event.text }; break;
    case "usage.updated": next.usage = { input: event.input_tokens, output: event.output_tokens, estimated: event.estimated }; break;
    case "message.delta": {
      const existing = state.items.find(item => item.kind === "message" && item.id === event.message_id);
      next.items = existing ? state.items.map(item => item === existing && item.kind === "message" ?
        { ...item, text: item.text + event.text } : item) :
        [...state.items, { kind: "message", id: event.message_id, text: event.text }];
      break;
    }
    case "tool.call": next.items = [...state.items, { kind: "tool", id: event.call_id, name: event.name, args: event.args }]; break;
    case "tool.result": next.items = state.items.map(item => item.kind === "tool" && item.id === event.call_id ? { ...item, result: event.text } : item); break;
    case "approval.requested": next.approvals = { ...state.approvals, [event.approval.approval_id]: event.approval }; next.approval = Object.values(next.approvals)[0] ?? null; break;
    case "approval.resolved": next.approvals = { ...state.approvals }; delete next.approvals[event.approval_id]; next.approval = Object.values(next.approvals)[0] ?? null; break;
    case "run.error": next.error = event.message; next.status = "error"; next.approval = null; next.approvals = {}; break;
    case "run.finished": next.status = event.status; next.approval = null; next.approvals = {}; next.questions = Object.fromEntries(Object.entries(state.questions).map(([id, record]) => [id, record.status === "pending" ? { ...record, status: "cancelled" } : record])); break;
  }
  return next;
}

export const useRun = create<RunState & { receive(event: HarnessEvent): void; reset(): void }>((set) => ({
  ...initialRun,
  receive: event => set(state => reduceEvent(state, event)),
  reset: () => set(initialRun),
}));
