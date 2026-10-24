import assert from "node:assert/strict";
import test from "node:test";
import { verifyCopy } from "../../src/i18n/verify-settings";
import { bounded } from "../../src/lib/localised-number";
import type { VerifySettingsResponse } from "../../src/lib/protocol";
import {
  BOUNDS,
  commandFor,
  compactionPercent,
  detectionLabel,
  keepMessages,
  percentText,
  shellOf,
  shellOptions,
  testModeOf,
  withContext,
  withTerminal,
  withVerify,
} from "../../src/lib/verify-settings";

const fa = verifyCopy("fa"), en = verifyCopy("en");

function document(overrides: Partial<VerifySettingsResponse> = {}): VerifySettingsResponse {
  return {
    context: { compaction_percent: 60, keep_messages: 8, offload: true, show_ring: true },
    verify: { gate: true, command: null, max_steps: 40, max_minutes: 30, fix_attempts: 3 },
    terminal: { shell: "auto", timeout_seconds: 120, max_output_lines: 200 },
    detection: { command: "pytest -q", source: "pyproject.toml" },
    ...overrides,
  };
}

test("a form edit rewrites one section and leaves the rest alone", () => {
  const value = document();
  const next = withContext(value, { compaction_percent: 75 });
  assert.equal(next.context?.compaction_percent, 75);
  assert.equal(next.context?.keep_messages, 8);
  assert.deepEqual(next.terminal, value.terminal);
  assert.deepEqual(next.verify, value.verify);
  // The document in hand is never mutated: the hook replaces it.
  assert.equal(value.context?.compaction_percent, 60);

  assert.equal(withVerify(value, { max_steps: 12 }).verify?.max_steps, 12);
  assert.equal(withVerify(value, { max_steps: 12 }).context?.compaction_percent, 60);
  assert.equal(withTerminal(value, { timeout_seconds: 30 }).terminal?.timeout_seconds, 30);
  assert.equal(withTerminal(value, { timeout_seconds: 30 }).terminal?.max_output_lines, 200);
});

test("a missing section is created rather than thrown away", () => {
  const empty: VerifySettingsResponse = {};
  assert.deepEqual(withContext(empty, { offload: false }).context, { offload: false });
  assert.deepEqual(withVerify(empty, { gate: false }).verify, { gate: false });
  assert.deepEqual(withTerminal(empty, { shell: "cmd" }).terminal, { shell: "cmd" });
});

test("every field is bounded by the backend's own limits", () => {
  assert.equal(bounded(0, BOUNDS.timeout.min, BOUNDS.timeout.max, BOUNDS.timeout.fallback), 1);
  assert.equal(bounded(900, BOUNDS.timeout.min, BOUNDS.timeout.max, BOUNDS.timeout.fallback), 600);
  assert.equal(bounded(10, BOUNDS.lines.min, BOUNDS.lines.max, BOUNDS.lines.fallback), 20);
  assert.equal(bounded(5000, BOUNDS.lines.min, BOUNDS.lines.max, BOUNDS.lines.fallback), 2000);
  assert.equal(bounded(25, BOUNDS.compaction.min, BOUNDS.compaction.max, BOUNDS.compaction.fallback), 30);
  assert.equal(bounded(95, BOUNDS.compaction.min, BOUNDS.compaction.max, BOUNDS.compaction.fallback), 90);
  assert.equal(bounded(99, BOUNDS.keep.min, BOUNDS.keep.max, BOUNDS.keep.fallback), 50);
  assert.equal(bounded(null, BOUNDS.steps.min, BOUNDS.steps.max, BOUNDS.steps.fallback), 40);
  // Half-typed input keeps the last good value instead of jumping to a bound.
  assert.equal(bounded(null, BOUNDS.fixes.min, BOUNDS.fixes.max, 7), 7);
});

test("the stored percent and keep count fall back to the mock's defaults", () => {
  assert.equal(compactionPercent(undefined), 60);
  assert.equal(compactionPercent({ compaction_percent: 45 }), 45);
  assert.equal(keepMessages({ keep_messages: 0 }), 0);
  assert.equal(keepMessages(undefined), 8);
  assert.equal(percentText(60, "fa"), "۶۰٪");
  assert.equal(percentText(60, "en"), "60٪");
});

test("a blank command reads as automatic, exactly like the backend", () => {
  assert.equal(testModeOf(undefined), "auto");
  assert.equal(testModeOf({ command: null }), "auto");
  assert.equal(testModeOf({ command: "   " }), "auto");
  assert.equal(testModeOf({ command: "pytest -x -q" }), "custom");
});

test("choosing a mode decides the command a save would run", () => {
  const detection = { command: "pytest -q", source: "pyproject.toml" as const };
  // Automatic clears the override so detection wins again.
  assert.equal(commandFor("auto", { command: "npm test" }, detection), null);
  // Custom keeps what was typed.
  assert.equal(commandFor("custom", { command: "npm test" }, detection), "npm test");
  // Custom starts from the detected command instead of an empty box.
  assert.equal(commandFor("custom", { command: null }, detection), "pytest -q");
  assert.equal(commandFor("custom", { command: "" }, undefined), "");
});

test("the detection row names the evidence, never a guess", () => {
  assert.deepEqual(detectionLabel({ command: "pytest -q", source: "pyproject.toml" }, fa), {
    command: "pytest -q", evidence: "از pyproject.toml", empty: null,
  });
  assert.deepEqual(detectionLabel({ command: "npm test", source: "package.json" }, en), {
    command: "npm test", evidence: "from package.json", empty: null,
  });
  // A custom command is the box below, not evidence from a file.
  assert.deepEqual(detectionLabel({ command: "pytest -x -q", source: "custom" }, fa), {
    command: "pytest -x -q", evidence: null, empty: null,
  });
  assert.deepEqual(detectionLabel({ command: null, source: "none" }, fa), {
    command: null, evidence: null, empty: "چیزی تشخیص داده نشد",
  });
  assert.deepEqual(detectionLabel(undefined, en), {
    command: null, evidence: null, empty: "Nothing detected",
  });
});

test("the shell list is the mock's three options with readable labels", () => {
  assert.deepEqual(shellOptions(fa), [
    { value: "auto", label: "خودکار" },
    { value: "powershell", label: "PowerShell" },
    { value: "cmd", label: "CMD" },
  ]);
  assert.equal(shellOptions(en)[0].label, "Automatic");
  // An unknown stored shell falls back to automatic instead of an empty select.
  assert.equal(shellOf({ shell: "auto" }), "auto");
  assert.equal(shellOf({ shell: "cmd" }), "cmd");
  assert.equal(shellOf({ shell: "fish" }), "auto");
  assert.equal(shellOf(undefined), "auto");
});
