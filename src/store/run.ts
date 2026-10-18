import { create } from "zustand";
import type { HarnessEvent } from "../lib/protocol";

export type TimelineItem = { kind: "message"; id: string; text: string } |
  { kind: "tool"; id: string; name: string; args: Record<string, unknown>; result?: string };
export interface RunState {
  runId: string | null;
  seq: number;
  task: string;
  status: "idle" | "running" | "completed" | "stopped" | "error";
  items: TimelineItem[];
  error: string | null;
}
export const initialRun: RunState = { runId: null, seq: 0, task: "", status: "idle", items: [], error: null };

export function reduceEvent(state: RunState, event: HarnessEvent): RunState {
  if (event.type === "run.started" && event.run_id !== state.runId) {
    return { ...initialRun, runId: event.run_id, seq: event.seq, task: event.task, status: "running" };
  }
  if (event.run_id !== state.runId || event.seq <= state.seq) return state;
  const next = { ...state, seq: event.seq };
  switch (event.type) {
    case "message.delta": {
      const existing = state.items.find(item => item.kind === "message" && item.id === event.message_id);
      next.items = existing ? state.items.map(item => item === existing && item.kind === "message" ?
        { ...item, text: item.text + event.text } : item) :
        [...state.items, { kind: "message", id: event.message_id, text: event.text }];
      break;
    }
    case "tool.call": next.items = [...state.items, { kind: "tool", id: event.call_id, name: event.name, args: event.args }]; break;
    case "tool.result": next.items = state.items.map(item => item.kind === "tool" && item.id === event.call_id ? { ...item, result: event.text } : item); break;
    case "run.error": next.error = event.message; next.status = "error"; break;
    case "run.finished": next.status = event.status; break;
  }
  return next;
}

export const useRun = create<RunState & { receive(event: HarnessEvent): void; reset(): void }>((set) => ({
  ...initialRun,
  receive: event => set(state => reduceEvent(state, event)),
  reset: () => set(initialRun),
}));
