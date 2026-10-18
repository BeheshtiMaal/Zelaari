import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { initialRun, reduceEvent } from "../../src/store/run";
import { decodeSSE } from "../../src/lib/sse";
import type { HarnessEvent } from "../../src/lib/protocol";

test("real engine event log replays to identical state through fragmented SSE", async () => {
  const contents = await readFile("artifacts/replay-events.jsonl", "utf8");
  const persisted = contents.trim().split(/\r?\n/).map(line => JSON.parse(line) as HarnessEvent);
  const encoder = new TextEncoder();
  const wire = encoder.encode(persisted.map(event => `id: ${event.seq}\r\ndata: ${JSON.stringify(event)}\r\n\r\n`).join(""));
  const stream = new ReadableStream<Uint8Array>({ start(controller) {
    for (let offset = 0; offset < wire.length; offset += 7) controller.enqueue(wire.slice(offset, offset + 7));
    controller.close();
  } });
  let live = initialRun;
  for await (const event of decodeSSE(stream)) live = reduceEvent(live, event);
  const replay = persisted.reduce(reduceEvent, initialRun);
  assert.deepEqual(live, replay);
  assert.equal(replay.status, "completed");
  assert.ok(replay.items.some(item => item.kind === "tool" && item.result));
  assert.ok(replay.items.some(item => item.kind === "message" && item.text.includes("Stack")));
  assert.deepEqual(persisted.reduce(reduceEvent, live), live, "duplicate events are idempotent");
});
