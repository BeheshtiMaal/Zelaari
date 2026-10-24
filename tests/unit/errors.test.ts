import assert from "node:assert/strict";
import { test } from "node:test";
import { commandTimeout, fill, jailBlock, toolFailure } from "../../src/lib/errors";

/** Byte-identical to `tools/jail.py:jail_message`; if this drifts, the card stops rendering. */
const blocked = (target: string) =>
  `Access blocked: ${target} is outside the workspace. Access is never allowed, even with approval.`;

test("a jail sentence yields the blocked path", () => {
  const failure = jailBlock(blocked("C:\\Users\\me\\secrets.txt"));
  assert.deepEqual(failure, { kind: "jail", path: "C:\\Users\\me\\secrets.txt" });
});

test("the jail prefix can follow a tool's own lead-in", () => {
  const text = `Read failed. ${blocked("/etc/passwd")}`;
  assert.deepEqual(jailBlock(text), { kind: "jail", path: "/etc/passwd" });
});

test("an ordinary failure is not a jail block", () => {
  assert.equal(jailBlock("Read denied: not a file or outside workspace"), null);
  assert.equal(jailBlock("Access blocked: but no closing sentence"), null);
});

test("a timed-out command yields the command and its budget", () => {
  const text = JSON.stringify({
    command: "Start-Sleep -Seconds 900", shell: "powershell", exit_code: null,
    timed_out: true, timeout_seconds: 120, output: "",
  });
  assert.deepEqual(commandTimeout(text), {
    kind: "timeout", command: "Start-Sleep -Seconds 900", seconds: 120,
  });
});

test("a finished command is not a timeout", () => {
  const text = JSON.stringify({ command: "dir", exit_code: 0, timed_out: false, timeout_seconds: 120 });
  assert.equal(commandTimeout(text), null);
});

test("a non-command tool result is not a timeout", () => {
  assert.equal(commandTimeout("written to /src/a.py"), null);
  assert.equal(commandTimeout('{"path":"/src/a.py"}'), null);
});

test("the timeout card wins over the jail card", () => {
  const text = JSON.stringify({ command: "ls", timed_out: true, timeout_seconds: 5 });
  assert.equal(toolFailure(text)?.kind, "timeout");
  assert.equal(toolFailure(blocked("/root"))?.kind, "jail");
  assert.equal(toolFailure("Edit denied: file not found"), null);
});

test("a crashed command reports an interruption, not a timeout", () => {
  assert.equal(toolFailure("Interrupted: the engine stopped before this command finished")?.kind, "interrupted");
  // The interruption notice is prose, so it wins before any JSON payload is considered.
  assert.equal(toolFailure('Interrupted: {"timed_out": true}')?.kind, "interrupted");
});

test("the card interpolates seconds in the active locale's digits", () => {
  assert.equal(fill("زمان {seconds} ثانیه", { seconds: 120 }, "fa"), "زمان ۱۲۰ ثانیه");
  assert.equal(fill("Stopped after {seconds}s", { seconds: 120 }, "en"), "Stopped after 120s");
});

test("an unknown placeholder is left alone", () => {
  assert.equal(fill("{seconds} / {missing}", { seconds: 5 }, "en"), "5 / {missing}");
});
