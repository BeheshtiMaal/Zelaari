import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { canConfirm, confirmFacts, confirmOutcome, describeKeys, describeRuns, formatBytes } from "../../src/lib/confirm";
import type { DataSummary } from "../../src/lib/protocol";

const summary = (over: Partial<DataSummary> = {}): DataSummary => ({
  app_data: "C:\\Users\\someone\\AppData\\Roaming\\CodeHarness",
  keys: 2,
  workspaces: [
    { path: "C:\\work\\alpha", name: "alpha", harness: "C:\\work\\alpha\\.harness", runs: 7, run_bytes: 2048, checkpoints_bytes: 1024, tasks: 3 },
    { path: "C:\\work\\beta", name: "beta", harness: "C:\\work\\beta\\.harness", runs: 1, run_bytes: 10, checkpoints_bytes: 0, tasks: 1 },
  ],
  ...over,
});

describe("confirmFacts", () => {
  it("reads the workspace that was asked about, not merely the first one", () => {
    const facts = confirmFacts(summary(), "C:\\work\\beta");
    assert.equal(facts.runs, 1);
    assert.equal(facts.tasks, 1);
    assert.equal(facts.bytes, 10);
    assert.equal(facts.harness, "C:\\work\\beta\\.harness");
  });

  it("counts run bytes and checkpoint bytes together, because both are removed", () => {
    assert.equal(confirmFacts(summary(), "C:\\work\\alpha").bytes, 3072);
  });

  it("falls back to the first workspace when the requested one is not in the summary", () => {
    const facts = confirmFacts(summary(), "C:\\work\\gone");
    assert.equal(facts.workspace, "C:\\work\\alpha");
    assert.equal(facts.runs, 7);
  });

  it("reads a missing summary as zeros, never as an unknown amount", () => {
    const facts = confirmFacts(null, "C:\\work\\alpha");
    assert.deepEqual(facts, { runs: 0, tasks: 0, bytes: 0, keys: 0, workspace: "C:\\work\\alpha", harness: "" });
  });

  it("counts keys from the summary, not from the workspaces", () => {
    assert.equal(confirmFacts(summary({ workspaces: [] }), "C:\\work\\alpha").keys, 2);
    assert.equal(confirmFacts(summary(), "C:\\work\\alpha").keys, 2);
  });

  it("survives a summary with no workspace list at all", () => {
    const facts = confirmFacts({ app_data: "C:\\data" }, "C:\\work\\alpha");
    assert.equal(facts.runs, 0);
    assert.equal(facts.keys, 0);
  });
});

describe("formatBytes", () => {
  it("keeps a byte count in bytes and never shows a fraction of one", () => {
    assert.equal(formatBytes(0, "en"), "0 B");
    assert.equal(formatBytes(999, "en"), "999 B");
  });

  it("steps up a unit at 1024 and keeps one decimal", () => {
    assert.equal(formatBytes(1024, "en"), "1 KB");
    assert.equal(formatBytes(1536, "en"), "1.5 KB");
    assert.equal(formatBytes(1024 * 1024 * 3, "en"), "3 MB");
  });

  it("stops at gigabytes instead of inventing a larger unit, and groups thousands", () => {
    assert.equal(formatBytes(1024 ** 4 * 5, "en"), "5,120 GB");
  });

  it("uses the locale's own digits and unit word", () => {
    assert.equal(formatBytes(1536, "fa"), "۱٫۵ کیلوبایت");
    assert.equal(formatBytes(0, "fa"), "۰ بایت");
  });

  it("treats a negative size as zero rather than showing a minus sign", () => {
    assert.equal(formatBytes(-5, "en"), "0 B");
  });
});

describe("describeRuns", () => {
  const facts = confirmFacts(summary(), "C:\\work\\alpha");

  it("puts the size in the sentence as text, never as a number to reformat", () => {
    assert.equal(describeRuns("{runs} runs · {size} · {tasks} tasks", facts, "en"), "7 runs · 3 KB · 3 tasks");
  });

  it("counts in the locale's digits and keeps the size's own unit", () => {
    assert.equal(describeRuns("{runs} اجرا · {size} · {tasks} کار", facts, "fa"), "۷ اجرا · ۳ کیلوبایت · ۳ کار");
  });

  it("leaves a placeholder it was not given alone", () => {
    assert.equal(describeRuns("{runs} of {total}", facts, "en"), "7 of {total}");
  });
});

describe("describeKeys", () => {
  it("counts keys in the locale's digits", () => {
    assert.equal(describeKeys("{keys} keys", confirmFacts(summary(), "C:\\work\\alpha"), "en"), "2 keys");
    assert.equal(describeKeys("{keys} کلید", confirmFacts(summary(), "C:\\work\\alpha"), "fa"), "۲ کلید");
  });
});

describe("canConfirm", () => {
  it("refuses the action until the acknowledgement is ticked", () => {
    assert.equal(canConfirm(false, false), false);
    assert.equal(canConfirm(true, false), true);
  });

  it("refuses while the action is already running", () => {
    assert.equal(canConfirm(true, true), false);
  });

  it("refuses when both the box is clear and the action is running", () => {
    assert.equal(canConfirm(false, true), false);
  });
});

describe("confirmOutcome", () => {
  it("closes only when the action reported success", () => {
    assert.equal(confirmOutcome(true), "close");
    assert.equal(confirmOutcome(false), "stay");
  });
});
