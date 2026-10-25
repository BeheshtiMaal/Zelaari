import assert from "node:assert/strict";
import { test } from "node:test";
import { activeCommand, commandMatches } from "../../src/lib/commands";
import type { SkillCommand } from "../../src/lib/protocol";

const list: SkillCommand[] = [
  { command: "/fix", name: "fix-failing-tests", description: "Reproduce, then fix." },
  { command: "/grill", name: "grill-me", description: "Interview first." },
  { command: "/search", name: "web-search", description: "Search the web.", requires_approval: true },
];

test("only leading command text opens the picker", () => {
  assert.deepEqual(commandMatches("/", list).map(item => item.command), ["/fix", "/grill", "/search"]);
  assert.deepEqual(commandMatches("/gr", list).map(item => item.command), ["/grill"]);
  for (const text of ["/unknown", "hello /grill", "/grill task", "plain text", "@context"]) {
    assert.deepEqual(commandMatches(text, list), []);
  }
});

test("an empty list offers nothing", () => {
  assert.deepEqual(commandMatches("/", []), []);
  assert.deepEqual(commandMatches("/gr", []), []);
});

test("the active command is the one the task already names", () => {
  assert.equal(activeCommand("/grill improve parser", list)?.name, "grill-me");
  assert.equal(activeCommand("/fix tests", list)?.name, "fix-failing-tests");
  assert.equal(activeCommand("/unknown thing", list), null);
  assert.equal(activeCommand("plain text", list), null);
});

test("a command from a disabled skill is not offered", () => {
  const only = list.filter(item => item.name === "grill-me");
  assert.deepEqual(commandMatches("/f", only), []);
  assert.deepEqual(commandMatches("/g", only).map(item => item.command), ["/grill"]);
});
