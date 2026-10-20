import type { ActivityScope, HarnessEvent, PlanRecord } from "./protocol";
import type { RunState } from "../store/run";

export type ScopedEvent = Extract<HarnessEvent, { scope: ActivityScope }>;
export function eventScope(event: HarnessEvent): ActivityScope | null {
  return "scope" in event ? event.scope ?? null : null;
}
export function groupEvents(events: HarnessEvent[], stepId: string | null) {
  return events.filter(event => (eventScope(event)?.step_id ?? null) === stepId);
}
export function countTools(events: HarnessEvent[]) {
  const calls = events.filter(event => event.type === "tool.call");
  return {
    read: calls.filter(e => ["read_file", "ls", "glob", "grep"].includes(e.name)).length,
    writes: calls.filter(e => ["write_file", "edit_file", "delete"].includes(e.name)).length,
    commands: calls.filter(e => ["run_command", "git_switch"].includes(e.name)).length,
  };
}
export function duration(start?: string | null, end?: string | null): number | null {
  if (!start || !end) return null;
  const value = Date.parse(end) - Date.parse(start);
  return Number.isFinite(value) ? Math.max(0, value / 1000) : null;
}
export function currentContext(events: HarnessEvent[]) {
  return events.slice().reverse().find(event => event.type === "context.updated" && event.scope.agent === "parent");
}
export function trustedPlan(plan: PlanRecord | null, runId: string | null, reference: { runId: string; planId: string; revision: string }) {
  return runId === reference.runId && plan?.run_id === runId && plan.plan_id === reference.planId && plan.revision === reference.revision ? plan : null;
}
export function taskFiles(events: HarnessEvent[]) {
  const files = new Map<string, "read" | "changed" | "pending">();
  const results = new Map(events.filter(e => e.type === "tool.result").map(e => [e.call_id, e.text]));
  for (const event of events) {
    if (event.type === "tool.call" && typeof event.args.file_path === "string") {
      if (!["read_file", "write_file", "edit_file", "delete"].includes(event.name)) continue;
      const write = ["write_file", "edit_file", "delete"].includes(event.name);
      const result = results.get(event.call_id);
      const failed = result && /permission denied|error|rejected/i.test(result);
      if (failed) continue;
      const state = write ? result && !failed ? "changed" : "pending" : "read";
      if (files.get(event.args.file_path) !== "changed") files.set(event.args.file_path, state);
    }
    if (event.type === "approval.requested" && event.approval.path && !files.has(event.approval.path)) files.set(event.approval.path, "pending");
  }
  return [...files.entries()];
}

export function thinkingState(scope: ActivityScope, events: HarnessEvent[]) {
  const scoped = events.filter(event => eventScope(event)?.scope_id === scope.scope_id);
  return { finished: scoped.some(e => e.type === "activity.finished"),
    reasoning: scoped.filter(e => e.type === "reasoning.delta").map(e => e.text).join("") };
}
export function eventBodyModel(events: HarnessEvent[], child: boolean) {
  const turns = events.filter(event => event.type === "activity.started").filter(event => child || event.scope.agent === "parent");
  const visible = events.filter(event => child || !eventScope(event) || eventScope(event)?.agent === "parent");
  return {
    turns,
    tools: visible.filter(e => e.type === "tool.call").map(event => ({ event,
      result: visible.slice().reverse().find(e => e.type === "tool.result" && e.call_id === event.call_id && eventScope(e)?.scope_id === event.scope?.scope_id),
    })),
    messages: [...new Set(visible.filter(e => e.type === "message.delta").map(e => e.message_id))].map(id => ({ id,
      text: visible.filter(e => e.type === "message.delta" && e.message_id === id).map(e => e.type === "message.delta" ? e.text : "").join(""),
    })),
  };
}
export function timelineGroups(run: RunState) {
  const groups = [{ id: null as string | null, title: null as string | null }, ...(run.plan?.submission.steps.map(step => ({ id: step.id as string | null, title: step.title as string | null })) ?? [])];
  return groups.map(group => {
    const events = groupEvents(run.events, group.id);
    const progress = run.plan?.progress.find(p => p.step_id === group.id);
    const active = (run.status === "running" && progress?.status === "in_progress") || (group.id === null && !run.plan);
    const terminal = group.id === null ? !!run.plan : progress?.status === "completed" || progress?.status === "failed" || run.status !== "running";
    const children = events.filter(e => e.type === "subagent.started").map(child => {
      const end = events.slice().reverse().find(e => e.type === "subagent.finished" && e.scope.scope_id === child.scope.scope_id);
      return { child, end, seconds: duration(child.ts, end?.ts),
        events: events.filter(e => eventScope(e)?.parent_scope_id === child.scope.scope_id) };
    });
    return { ...group, events, progress, active, terminal, children, counts: countTools(events),
      elapsed: duration(progress?.started_at, progress?.ended_at),
      summaries: events.filter(e => e.type === "context.summarized"),
      visible: group.id !== null || !events.every(e => ["run.started", "usage.updated", "steering.updated"].includes(e.type)),
      reasoningAvailable: events.some(e => e.type === "reasoning.delta"),
      reasoningFinished: events.some(e => e.type === "activity.finished"),
    };
  }).filter(group => group.visible);
}
