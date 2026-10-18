import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test, mock } from "node:test";
import { initialRun, reduceEvent } from "../../src/store/run";
import { decodeSSE, subscribe } from "../../src/lib/sse";
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

test("client reconnects a truncated stream with the last applied event id", async () => {
  const source = (await readFile("artifacts/replay-events.jsonl", "utf8")).trim().split(/\r?\n/).map(line => JSON.parse(line) as HarnessEvent);
  const cursors: string[] = [];
  const stub = mock.method(globalThis, "fetch", async (_url: unknown, options: RequestInit) => {
    const cursor = (options.headers as Record<string, string>)["Last-Event-ID"];
    cursors.push(cursor);
    const batch = cursors.length === 1 ? source.slice(0, 3) : source.slice(3);
    return new Response(batch.map(event => `data: ${JSON.stringify(event)}\n\n`).join(""), { headers: { "Content-Type": "text/event-stream" } });
  });
  try {
    const received: HarnessEvent[] = [];
    await subscribe("http://127.0.0.1:1", "synthetic", source[0].run_id, event => received.push(event), new AbortController().signal);
    assert.deepEqual(cursors, ["0", "3"]);
    assert.deepEqual(received, source);
  } finally { stub.mock.restore(); }
});
