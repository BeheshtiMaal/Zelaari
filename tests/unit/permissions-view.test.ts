import assert from "node:assert/strict";
import { test } from "node:test";
import { KNOWN_LOCKED, MODES, defaultRows, explicitRows, lockedKey, lockedRows, ruleRows, scopeLabel } from "../../src/lib/permissions-view";
import type { RulesResponse } from "../../src/lib/protocol";

const ENGINE = [".harness/ writes", "web_search queries", "MCP tool calls", "high-risk commands", "timeouts above the default"];

function response(overrides: Partial<RulesResponse> = {}): RulesResponse {
  return { mode: "ask", rules: { mode: "ask" }, tools: {}, defaults: {}, always_ask: ENGINE, ...overrides };
}

test("the always-ask list is the engine's five, the mock's three first", () => {
  const { rows, assumed } = lockedRows(ENGINE);
  assert.equal(assumed, false);
  assert.deepEqual(rows.map(row => row.key), ["storage", "web", "commands", "mcp", "timeout"]);
  assert.equal(rows.length, 5);
});

test("an unreadable list fails closed to every known condition", () => {
  for (const value of [undefined, null, [], [""], ["  "]]) {
    const { rows, assumed } = lockedRows(value);
    assert.equal(assumed, true);
    assert.deepEqual(rows.map(row => row.key), [...KNOWN_LOCKED]);
  }
});

test("a condition the engine adds later is still shown, still locked", () => {
  const { rows, assumed } = lockedRows([...ENGINE, "kernel panic"]);
  assert.equal(assumed, false);
  assert.equal(rows.length, 6);
  assert.equal(rows.at(-1)?.key, "other");
  assert.equal(rows.at(-1)?.text, "kernel panic");
});

test("the engine string decides the row, not its position", () => {
  assert.equal(lockedKey(".harness/ writes"), "storage");
  assert.equal(lockedKey("web_search queries"), "web");
  assert.equal(lockedKey("MCP tool calls"), "mcp");
  assert.equal(lockedKey("high-risk commands"), "commands");
  assert.equal(lockedKey("timeouts above the default"), "timeout");
  assert.equal(lockedKey("something new"), "other");
  const shuffled = lockedRows([...ENGINE].reverse());
  assert.deepEqual(shuffled.rows.map(row => row.key), ["storage", "web", "commands", "mcp", "timeout"]);
});

test("a locked row carries no decision, so nothing can make it editable", () => {
  for (const row of lockedRows(ENGINE).rows) assert.deepEqual(Object.keys(row), ["key", "text"]);
});

test("the modes are the mock's, in the mock's order", () => {
  assert.deepEqual(MODES, ["read-only", "ask", "auto"]);
});

test("a tool with several rules shows its strictest decision and every scope", () => {
  const rows = explicitRows(response({
    tools: {
      edit_file: [{ glob: "src/**", action: "allow" }, { glob: "secrets/**", action: "deny" }],
      read_file: [{ glob: "*", action: "allow" }],
      run_command: [{ glob: "*", action: "ask" }],
    },
  }));
  assert.deepEqual(rows.map(row => row.tool), ["edit_file", "read_file", "run_command"]);
  assert.deepEqual(rows[0], { tool: "edit_file", globs: ["src/**", "secrets/**"], action: "deny" });
  assert.equal(rows[1].action, "allow");
  assert.equal(rows[2].action, "ask");
});

test("a rule with no glob covers the whole tool", () => {
  const rows = explicitRows(response({ tools: { delete: [{ action: "deny" }] } }));
  assert.deepEqual(rows[0].globs, ["*"]);
  assert.equal(scopeLabel(rows[0]), "*");
});

test("an unknown action is treated as asking, never as allowing", () => {
  const rows = explicitRows(response({ tools: { edit_file: [{ glob: "src/**", action: "sometimes" }] } }));
  assert.equal(rows[0].action, "ask");
});

test("the grid falls back to the mode's defaults when the workspace wrote no rule", () => {
  const defaults = { read: "allow", write: "ask", delete: "deny", command: "ask", web: "ask", mcp: "ask", internal: "allow", ui: "allow" };
  const fromDefaults = ruleRows(response({ defaults }));
  assert.equal(fromDefaults.fromDefaults, true);
  assert.deepEqual(fromDefaults.rows.map(row => row.tool), Object.keys(defaults));
  assert.deepEqual(defaultRows(response({ defaults })).map(row => row.action), ["allow", "ask", "deny", "ask", "ask", "ask", "allow", "allow"]);
  const written = ruleRows(response({ defaults, tools: { edit_file: [{ glob: "src/**", action: "ask" }] } }));
  assert.equal(written.fromDefaults, false);
  assert.deepEqual(written.rows.map(row => row.tool), ["edit_file"]);
});

test("a missing response yields no rows and no crash", () => {
  assert.deepEqual(explicitRows(undefined), []);
  assert.deepEqual(defaultRows(null), []);
  assert.deepEqual(ruleRows(undefined), { rows: [], fromDefaults: true });
  assert.equal(lockedRows(undefined).assumed, true);
});
