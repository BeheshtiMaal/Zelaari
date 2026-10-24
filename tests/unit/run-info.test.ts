import assert from "node:assert/strict";
import test from "node:test";
import { planningCopy } from "../../src/i18n/planning";
import type { HarnessEvent } from "../../src/lib/protocol";
import { budgetOf, limitRows, occupancy } from "../../src/lib/run-info";

const fa = planningCopy("fa"), en = planningCopy("en");

const base = { run_id: "r1", ts: "2026-10-24T10:00:00Z", scope: { scope_id: "parent", agent: "parent" as const } };

function budget(seq: number, steps: number, fix: number) {
  return {
    ...base, seq, type: "budget.updated" as const,
    steps, max_steps: 40, fix_attempts: fix, max_fix_attempts: 3, elapsed_ms: 12_000, max_seconds: 1800,
  };
}

test("the panel reads the last budget the engine reported", () => {
  const events = [budget(2, 4, 0), budget(6, 11, 2)] as HarnessEvent[];
  assert.equal(budgetOf(events)?.steps, 11);
  assert.equal(budgetOf([]), null);
  // Events from an older run are not in this state, but a missing budget is honest about itself.
  assert.equal(budgetOf([{ ...base, seq: 1, type: "run.started", task: "t", workspace: "/w", model: "demo", mode: "auto", worktree: false } as HarnessEvent]), null);
});

test("the limit rows are real counters in the reader's digits", () => {
  const rows = limitRows(budget(3, 11, 0) as never, fa, "fa");
  assert.deepEqual(rows, [
    { key: "steps", label: "گام‌ها", value: "۱۱ از ۴۰" },
    { key: "fixes", label: "تلاش اصلاح این مرحله", value: "۰ از ۳" },
  ]);
  assert.deepEqual(limitRows(budget(3, 11, 0) as never, en, "en"), [
    { key: "steps", label: "Steps", value: "11 of 40" },
    { key: "fixes", label: "Fix attempts this step", value: "0 of 3" },
  ]);
  // No event yet means no numbers at all, not zeros pretending to be measurements.
  assert.deepEqual(limitRows(null, fa, "fa"), []);
});

test("occupancy reads like the mock and marks an estimate", () => {
  const measured = occupancy(48800, 128000, { used: false, window: false }, "fa", "از");
  assert.equal(measured?.text, "۳۸٪ · ۴۸٫۸K از ۱۲۸٫۰K");
  assert.equal(measured?.fraction, 0.38125);
  assert.equal(occupancy(48800, 128000, { used: false, window: false }, "en", "of")?.text, "38٪ · 48.8K of 128.0K");
  // Either side may be an estimate, and the marker says which.
  assert.equal(occupancy(48800, 128000, { used: true, window: false }, "fa", "از")?.text, "۳۸٪ · ~۴۸٫۸K از ۱۲۸٫۰K");
  assert.equal(occupancy(48800, 128000, { used: false, window: true }, "fa", "از")?.text, "۳۸٪ · ۴۸٫۸K از ~۱۲۸٫۰K");
});

test("occupancy is unknown without a window, and never overflows", () => {
  assert.equal(occupancy(48800, null, { used: false, window: false }, "fa", "از"), null);
  assert.equal(occupancy(48800, 0, { used: false, window: false }, "fa", "از"), null);
  const full = occupancy(200000, 128000, { used: false, window: false }, "fa", "از");
  assert.equal(full?.fraction, 1);
  assert.equal(full?.text, "۱۰۰٪ · ۲۰۰٫۰K از ۱۲۸٫۰K");
});
