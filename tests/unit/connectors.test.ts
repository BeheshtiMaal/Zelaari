import assert from "node:assert/strict";
import { test } from "node:test";
import type { ConnectorStatus, McpServerInput } from "../../src/lib/protocol";

/** The payload the add dialog submits: a transport picks exactly one of command or URL. */
function serverPayload(draft: McpServerInput, env: string): McpServerInput {
  return {
    ...draft,
    command: draft.transport === "stdio" ? draft.command : null,
    url: draft.transport === "http" ? draft.url : null,
    env_keys: env.split(",").map(item => item.trim()).filter(Boolean),
  };
}

function statusLabel(server: ConnectorStatus): string {
  if (!server.enabled) return "disabled";
  if (server.status === "connected") return "connected";
  if (server.status === "error") return "error";
  return "disabled";
}

test("a stdio server keeps its command and drops the URL", () => {
  const payload = serverPayload(
    { name: "files", transport: "stdio", command: "node server.js", url: "https://x.test" }, "",
  );
  assert.equal(payload.command, "node server.js");
  assert.equal(payload.url, null);
});

test("an http server keeps its URL and drops the command", () => {
  const payload = serverPayload(
    { name: "remote", transport: "http", command: "node", url: "https://x.test/mcp" }, "",
  );
  assert.equal(payload.command, null);
  assert.equal(payload.url, "https://x.test/mcp");
});

test("environment names are split, trimmed and emptied", () => {
  assert.deepEqual(serverPayload({ name: "a", transport: "stdio", command: "x" }, " A , ,B ").env_keys, ["A", "B"]);
  assert.deepEqual(serverPayload({ name: "a", transport: "stdio", command: "x" }, "").env_keys, []);
});

test("a server card reports what it can do", () => {
  assert.equal(statusLabel({ name: "a", enabled: true, status: "connected" }), "connected");
  assert.equal(statusLabel({ name: "a", enabled: true, status: "error" }), "error");
  assert.equal(statusLabel({ name: "a", enabled: false, status: "error" }), "disabled");
});

test("a tool is addressed as server__tool", () => {
  const server: ConnectorStatus = {
    name: "files", enabled: true, status: "connected",
    tools: [{ name: "read", namespaced: "files__read", description: "Read a file." }],
  };
  assert.deepEqual(server.tools?.map(tool => tool.namespaced), ["files__read"]);
  assert.equal(server.tools?.length, 1);
});
