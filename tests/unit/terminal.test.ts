import assert from "node:assert/strict";
import test from "node:test";
import { commandResult, killNote, visibleOutput } from "../../src/lib/terminal";

const copy = { killed: "The process and its children were killed.", silent: "(no output for {seconds} seconds)" };

test("a command result is read from the real payload", () => {
  const parsed = commandResult(JSON.stringify({
    command: "pytest -q", exit_code: 1, output: "1 failed\n11 passed\n", timed_out: false,
    timeout_seconds: 120, truncated: false, total_lines: 2,
  }));
  assert.equal(parsed?.exitCode, 1);
  assert.equal(parsed?.output, "1 failed\n11 passed\n");
  assert.equal(parsed?.timedOut, false);
});

test("anything that is not a command result stays text", () => {
  assert.equal(commandResult("plain output"), null);
  assert.equal(commandResult("[1,2,3]"), null);
  assert.equal(commandResult(JSON.stringify({ text: "hi" })), null);
  assert.equal(commandResult(JSON.stringify({ output: "x", exit_code: null }))?.exitCode, null);
});

test("the body is bounded by the line limit and says what is hidden", () => {
  const parsed = commandResult(JSON.stringify({ output: "a\nb\nc\nd\n", exit_code: 0 }))!;
  assert.deepEqual(visibleOutput(parsed, 2), { text: "a\nb", hidden: 2 });
  assert.deepEqual(visibleOutput(parsed, 200), { text: "a\nb\nc\nd", hidden: 0 });
  // A trailing newline is not an extra empty line.
  assert.deepEqual(visibleOutput(commandResult(JSON.stringify({ output: "", exit_code: 0 }))!, 5), { text: "", hidden: 0 });
});

test("the kill note names the real wait", () => {
  const note = killNote(120, copy);
  assert.match(note, /\(no output for 120 seconds\)/);
  assert.match(note, /killed/);
});
