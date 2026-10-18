import type { HarnessEvent } from "./protocol";

export async function* decodeSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<HarnessEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      pending += decoder.decode(value, { stream: !done });
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(pending))) {
        const block = pending.slice(0, boundary.index);
        pending = pending.slice(boundary.index + boundary[0].length);
        const data = block.split(/\r?\n/).filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
        if (data) yield JSON.parse(data) as HarnessEvent;
      }
      if (done) return;
    }
  } finally { reader.releaseLock(); }
}

export async function subscribe(
  baseUrl: string, token: string, runId: string, receive: (event: HarnessEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let seq = 0;
  let attempts = 0;
  while (!signal.aborted) {
    try {
      const response = await fetch(`${baseUrl}/runs/${runId}/events`, {
        headers: { Authorization: `Bearer ${token}`, "Last-Event-ID": String(seq) }, signal,
      });
      if (!response.ok || !response.body) throw new Error("Event stream unavailable");
      for await (const event of decodeSSE(response.body)) {
        if (event.seq <= seq) continue;
        if (event.seq !== seq + 1) throw new Error("Event sequence gap");
        receive(event); seq = event.seq; attempts = 0;
        if (event.type === "run.finished") return;
      }
    } catch (error) { if (signal.aborted) return; if (++attempts > 5) throw error; }
    await new Promise<void>(resolve => {
      const timer = setTimeout(resolve, 250);
      signal.addEventListener("abort", () => { clearTimeout(timer); resolve(); }, { once: true });
    });
  }
}
