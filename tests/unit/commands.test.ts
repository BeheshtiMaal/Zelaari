import assert from "node:assert/strict";
import { test } from "node:test";
import { commandMatches } from "../../src/lib/commands";
test("only leading supported command text opens the picker", () => {
  assert.deepEqual(commandMatches("/"), ["/grill"]);
  assert.deepEqual(commandMatches("/gr"), ["/grill"]);
  for (const text of ["/unknown", "hello /grill", "/grill task", "plain text", "@context"]) assert.deepEqual(commandMatches(text), []);
});
