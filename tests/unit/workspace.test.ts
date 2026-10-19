import assert from "node:assert/strict";
import { test } from "node:test";
import { approvalView, decision, keyAction } from "../../src/lib/approvals";
import {
  changedLineSet, childPath, entriesOf, fileOf, isSystemPath, parentPath, sortEntries, workspaceSubtitle,
} from "../../src/lib/files";
import type { ApprovalRequest, FileEntry, FileListing } from "../../src/lib/protocol";
import { initialRun, reduceEvent } from "../../src/store/run";

const approval: ApprovalRequest = {
  approval_id: "call-1", run_id: "run-1", kind: "tool", tool: "write_file", path: "src/a.py",
  command: null, risk: { level: "high", reasons: ["recursive or forced delete"] }, reason: "default write policy",
};

test("an approval event pauses the run and a resolution clears it", () => {
  const started = reduceEvent(initialRun, {
    type: "run.started", run_id: "run-1", seq: 1, ts: "2026-01-01T00:00:00Z", task: "t", model: "demo",
  });
  const paused = reduceEvent(started, {
    type: "approval.requested", run_id: "run-1", seq: 2, ts: "2026-01-01T00:00:01Z", approval,
  });
  assert.equal(paused.approval?.approval_id, "call-1");
  assert.equal(paused.status, "running", "a paused run is still a live run");

  const resumed = reduceEvent(paused, {
    type: "approval.resolved", run_id: "run-1", seq: 3, ts: "2026-01-01T00:00:02Z",
    approval_id: "call-1", decision: "approve", reason: null,
  });
  assert.equal(resumed.approval, null);
});

test("a finished run drops any stale approval", () => {
  const paused = { ...initialRun, runId: "run-1", seq: 2, approval };
  const done = reduceEvent(paused, {
    type: "run.finished", run_id: "run-1", seq: 3, ts: "2026-01-01T00:00:03Z", status: "completed",
  });
  assert.equal(done.approval, null);
  assert.equal(done.status, "completed");
});

test("the modal shows a command as a command and a path as a path", () => {
  const command = approvalView({ ...approval, tool: "run_command", path: null, command: "rm -rf build" });
  assert.equal(command.targetIsCommand, true);
  assert.equal(command.target, "rm -rf build");
  assert.equal(command.risk, "high");
  assert.deepEqual(command.reasons, ["recursive or forced delete"]);

  const path = approvalView(approval);
  assert.equal(path.targetIsCommand, false);
  assert.equal(path.target, "src/a.py");
});

test("Enter approves, Escape rejects, everything else is ignored", () => {
  assert.equal(keyAction("Enter"), "approve");
  assert.equal(keyAction("Escape"), "reject");
  assert.equal(keyAction("a"), null);
  assert.equal(keyAction("Tab"), null);
});

test("a rejection carries its reason only when there is one", () => {
  assert.deepEqual(decision("approve"), { decision: "approve" });
  assert.deepEqual(decision("reject"), { decision: "reject" });
  assert.deepEqual(decision("reject", "not now"), { decision: "reject", reason: "not now" });
});

test("tree paths join and split at the workspace root", () => {
  assert.equal(childPath("", "src"), "src");
  assert.equal(childPath("src", "a.py"), "src/a.py");
  assert.equal(parentPath("src/a.py"), "src");
  assert.equal(parentPath("a.py"), "");
  assert.equal(isSystemPath(".harness/rules.json"), true);
  assert.equal(isSystemPath("src/a.py"), false);
});

test("entries are ordered folders first, case-insensitively", () => {
  const entries: FileEntry[] = [
    { name: "zebra.md", path: "zebra.md", kind: "file", size: 1, changed: false },
    { name: "Alpha", path: "Alpha", kind: "dir", size: 0, changed: false },
    { name: "apple.md", path: "apple.md", kind: "file", size: 2, changed: true },
  ];
  assert.deepEqual(sortEntries(entries).map(entry => entry.name), ["Alpha", "apple.md", "zebra.md"]);
});

test("changed ranges become the exact line set the viewer highlights", () => {
  assert.deepEqual([...changedLineSet([[2, 4], [9, 9]])], [2, 3, 4, 9]);
  assert.equal(changedLineSet(undefined).size, 0);
  assert.equal(changedLineSet([]).size, 0);
});

test("a listing exposes either entries or a file, never both", () => {
  const folder: FileListing = { path: "", kind: "dir", entries: [{ name: "a.py", path: "a.py", kind: "file", size: 3, changed: false }], file: null };
  const file: FileListing = { path: "a.py", kind: "file", entries: [], file: { path: "a.py", text: "x", binary: false, truncated: false, changed_lines: [], pending_approval: true } };
  assert.equal(entriesOf(folder).length, 1);
  assert.equal(fileOf(folder), null);
  assert.equal(entriesOf(file).length, 0);
  assert.equal(fileOf(file)?.pending_approval, true);
});

test("the subtitle names the branch only when there is one", () => {
  assert.equal(workspaceSubtitle("D:\\p", "main"), "D:\\p · main");
  assert.equal(workspaceSubtitle("D:\\p", null), "D:\\p");
});
