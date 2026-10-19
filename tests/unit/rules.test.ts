import assert from "node:assert/strict";
import { test } from "node:test";
import { rulesRows, rulesValue } from "../../src/lib/use-rules";
import { initialRun, reduceEvent } from "../../src/store/run";
import type { HarnessEvent } from "../../src/lib/protocol";

test("rules rows preserve same-tool order and independent tool/path actions", () => {
  const value = rulesValue("ask", [{ tool: "edit_file", glob: "src/**", action: "allow" }, { tool: "edit_file", glob: "protected/**", action: "deny" }]);
  assert.deepEqual(rulesRows(value).map(row => row.action), ["allow", "deny"]);
  assert.throws(() => rulesValue("ask", [{ tool: "", glob: "*", action: "allow" }]));
});
test("parallel approval reduction keeps remaining decisions after partial resolution and ignores replay", () => {
  const start: HarnessEvent = { type: "run.started", run_id: "r", seq: 1, task: "fixture", model: "demo" };
  let state = reduceEvent(initialRun, start);
  for (const [index, id] of ["a", "b"].entries()) state = reduceEvent(state, {
    type: "approval.requested", run_id: "r", seq: index + 2,
    approval: { run_id: "r", approval_id: id, kind: "tool", tool: "edit_file" },
  });
  const resolved: HarnessEvent = { type: "approval.resolved", run_id: "r", seq: 4, approval_id: "a", decision: "reject" };
  state = reduceEvent(state, resolved);
  assert.equal(state.approval?.approval_id, "b");
  assert.deepEqual(Object.keys(state.approvals), ["b"]);
  assert.equal(reduceEvent(state, resolved), state);
});
