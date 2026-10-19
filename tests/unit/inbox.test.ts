import assert from "node:assert/strict";
import { test } from "node:test";
import { diffLines } from "../../src/lib/diff";
import { filteredApprovals, pendingCount, suggestedGlob, waitingRunIds, taskNeedsAttention } from "../../src/lib/inbox";
import { reviewShortcut } from "../../src/lib/approvals";
import type { ApprovalRecord } from "../../src/lib/protocol";

function record(id: string, run: string, status: ApprovalRecord["status"] = "pending"): ApprovalRecord {
  return { request: { approval_id: id, run_id: run, kind: "tool", tool: "edit_file", path: "src/a.py", created_at: "2026-10-19T00:00:00Z" }, interrupt_id: "barrier", status };
}
test("inbox filters approvals and counts pending decisions independently across tasks", () => {
  const records = [record("one", "a"), record("two", "a"), record("three", "b"), record("old", "c", "approved")];
  assert.equal(pendingCount(records), 3);
  assert.deepEqual([...waitingRunIds(records)], ["a", "b"]);
  assert.equal(filteredApprovals(records, "approved").length, 1);
  records[0].status = "rejected";
  assert.equal(pendingCount(records), 2);
  assert.ok(waitingRunIds(records).has("a"));
  assert.equal(suggestedGlob(records[0].request), "src/**");
  assert.equal(suggestedGlob({ ...records[0].request, path: ".harness/rules.json" }), null);
});
test("question waiting survives resolved approvals and schedule metadata counts only approvals", () => {
  const scheduled = record("schedule", "scheduled-run"); scheduled.request.source_kind = "schedule";
  const resolved = record("answered", "task", "approved");
  const task = { id: "task", workspace: "second-workspace", model: "demo", title: "Question", waiting_on: ["question" as const] };
  assert.equal(pendingCount([scheduled, resolved]), 1);
  assert.equal(taskNeedsAttention(task, [scheduled, resolved]), true);
  assert.equal(taskNeedsAttention({ ...task, waiting_on: [] }, [scheduled, resolved]), false);
});
test("diff line numbers track independent old/new positions over multiple hunks", () => {
  const lines = diffLines("--- a\n+++ a\n@@ -12,2 +12,3 @@\n def f():\n-old\n+new\n+extra\n@@ -30 +31 @@\n---content\n+++content\n");
  assert.equal(lines[4].old, 13);
  assert.equal(lines[5].next, 13);
  assert.equal(lines[6].next, 14);
  assert.equal(lines[8].kind, "remove");
  assert.equal(lines[8].old, 30);
  assert.equal(lines[9].kind, "add");
  assert.equal(lines[9].next, 31);
});
test("review shortcuts leave editable controls and focused button activation alone", () => {
  for (const tag of ["INPUT", "TEXTAREA", "SELECT"]) {
    assert.equal(reviewShortcut("Enter", tag), null);
    assert.equal(reviewShortcut("Escape", tag), null);
  }
  assert.equal(reviewShortcut("Enter", "DIV", true), null);
  assert.equal(reviewShortcut("Enter", "BUTTON"), null);
  assert.equal(reviewShortcut("Escape", "BUTTON"), "reject");
  assert.equal(reviewShortcut("Enter", "SECTION"), "approve");
});
