import assert from "node:assert/strict";
import test from "node:test";
import { disclosureValue } from "../../src/lib/use-disclosure";
import { countTools, duration, eventBodyModel, groupEvents, timelineGroups, trustedPlan } from "../../src/lib/timeline";
import { initialRun, reduceEvent } from "../../src/store/run";
import type { HarnessEvent, PlanRecord } from "../../src/lib/protocol";
import { planReviewReason, planReviewSteps } from "../../src/lib/plan-review";

const plan: PlanRecord = { run_id: "run", plan_id: "plan", revision: "a".repeat(64), baseline_ids: ["s"],
  submission: { steps: [{ id: "s", title: "Read" }] }, progress: [{ step_id: "s", status: "pending" }],
  adoption: "automatic", file_scope: { revision: "b".repeat(64) }, settings: {} };
test("trusted plan references reject forged run, identity and stale revision", () => {
  const reference = { runId: "run", planId: "plan", revision: plan.revision };
  assert.equal(trustedPlan(plan, "run", reference), plan);
  for (const key of ["runId", "planId", "revision"] as const) assert.equal(trustedPlan(plan, "run", { ...reference, [key]: "forged" }), null);
  assert.equal(trustedPlan(null, "run", reference), null);
});
test("plan approval details use the reviewed proposal and explain the actual gate", () => {
  const request = { run_id: "run", approval_id: "review", tool: "submit_plan", kind: "tool" as const,
    reason: "Plan review: added_steps, dropped_step", plan_proposed: { steps: [{ id: "s", title: "Human reviewed", expected_files: ["src/*.py"], verify_command: "pytest" }] } };
  assert.match(planReviewReason(request, "en") ?? "", /More than two steps/);
  assert.match(planReviewReason(request, "en") ?? "", /step would be dropped/);
  assert.deepEqual(planReviewSteps(request), [{ id: "s", title: "Human reviewed", files: ["src/*.py"], verify: "pytest" }]);
});
test("ended Thinking collapses once and preserves manual reopening through subsequent updates", () => {
  const active = disclosureValue(undefined, true, false);
  const ended = disclosureValue(active, false, true);
  assert.equal(active.open, true); assert.equal(ended.open, false);
  const manual = { ...ended, open: true };
  assert.equal(disclosureValue(manual, false, true), manual);
});
test("plan progress and steering replay are idempotent and stale revisions cannot replace progress", () => {
  const events: HarnessEvent[] = [
    { type: "run.started", run_id: "run", seq: 1, task: "Read", model: "demo" },
    { type: "plan.created", run_id: "run", seq: 2, plan },
    { type: "plan.step.updated", run_id: "run", seq: 3, plan_id: "plan", revision: plan.revision, progress: { step_id: "s", status: "in_progress" } },
    { type: "plan.step.updated", run_id: "run", seq: 4, plan_id: "plan", revision: "wrong", progress: { step_id: "s", status: "completed" } },
  ];
  const state = events.reduce(reduceEvent, initialRun);
  assert.equal(state.plan?.adoption, "automatic"); assert.equal(state.plan?.progress[0].status, "in_progress");
  assert.deepEqual(events.reduce(reduceEvent, state), state);
});
test("step counts keep concurrent child scopes and legacy analysis separate", () => {
  const events: HarnessEvent[] = [
    { type: "tool.call", run_id: "run", seq: 1, call_id: "read", name: "read_file", args: {} },
    { type: "tool.call", run_id: "run", seq: 2, call_id: "read", name: "read_file", args: {}, scope: { scope_id: "child", step_id: "s", agent: "reviewer" } },
    { type: "tool.call", run_id: "run", seq: 3, call_id: "write", name: "write_file", args: {}, scope: { scope_id: "parent", step_id: "s" } },
  ];
  assert.equal(groupEvents(events, null).length, 1);
  assert.deepEqual(countTools(groupEvents(events, "s")), { read: 1, writes: 1, commands: 0 });
  assert.equal(duration("2026-10-20T00:00:00Z", "2026-10-20T00:01:00Z"), 60);
  assert.equal(duration(null, null), null);
});
test("an action interrupted before a stop or crash keeps its step open and notices the user", () => {
  const active = disclosureValue(undefined, true, false);
  const ended = disclosureValue(active, false, true, true);
  assert.equal(ended.open, true);
  const collapsed = { ...ended, open: false };
  assert.equal(disclosureValue(collapsed, false, true, true).open, false);
  const events: HarnessEvent[] = [
    { type: "run.started", run_id: "run", seq: 1, task: "Command", model: "demo" },
    { type: "plan.created", run_id: "run", seq: 2, plan },
    { type: "tool.call", run_id: "run", seq: 3, call_id: "c", name: "run_command", args: { command: "x" }, scope: { scope_id: "a", agent: "parent", step_id: "s" } },
    { type: "tool.result", run_id: "run", seq: 4, call_id: "c", text: "Interrupted: this action may have run before the engine stopped.", scope: { scope_id: "a", agent: "parent", step_id: "s" } },
    { type: "run.finished", run_id: "run", seq: 5, status: "completed" },
  ];
  const state = events.reduce(reduceEvent, initialRun);
  assert.equal(timelineGroups(state).find(group => group.id === "s")?.attention, true);
  assert.equal(timelineGroups(state).find(group => group.id === null)?.attention, false);
});

test("a recovered call shows the interrupted result reported by the next activity", () => {
  const events: HarnessEvent[] = [
    { type: "run.started", run_id: "run", seq: 1, task: "Command", model: "demo" },
    { type: "plan.created", run_id: "run", seq: 2, plan },
    { type: "activity.started", run_id: "run", seq: 3, scope: { scope_id: "before", agent: "parent", step_id: "s" } },
    { type: "tool.call", run_id: "run", seq: 4, call_id: "c", name: "run_command", args: { command: "x" }, scope: { scope_id: "before", agent: "parent", step_id: "s" } },
    { type: "activity.finished", run_id: "run", seq: 5, status: "interrupted", scope: { scope_id: "before", agent: "parent", step_id: "s" } },
    { type: "activity.started", run_id: "run", seq: 6, scope: { scope_id: "after", agent: "parent", step_id: "s" } },
    { type: "tool.result", run_id: "run", seq: 7, call_id: "c", text: "Interrupted: this action may have run before the engine stopped.", scope: { scope_id: "after", agent: "parent", step_id: "s" } },
    { type: "run.finished", run_id: "run", seq: 8, status: "completed" },
  ];
  const state = events.reduce(reduceEvent, initialRun);
  const group = timelineGroups(state).find(candidate => candidate.id === "s")!;
  const [tool] = eventBodyModel(group.events, false).tools;
  assert.equal(tool.result?.type === "tool.result" ? tool.result.text.slice(0, 12) : null, "Interrupted:");
  assert.equal(group.attention, true);
});
