import { useRef, useState } from "react";
import { api } from "./api";
import type { SteeringRecord } from "./protocol";
import { useRun } from "../store/run";

export function useSteering() {
  const [error, setError] = useState(false), [sending, setSending] = useState(false);
  const pending = useRef<{ id: string; text: string; runId: string } | null>(null);
  async function send(text: string) {
    const run = useRun.getState();
    if (!run.runId || run.status !== "running" || sending || !text.trim()) return false;
    if (pending.current?.text !== text || pending.current.runId !== run.runId) pending.current = { id: crypto.randomUUID(), text, runId: run.runId };
    setSending(true); setError(false);
    try {
      await api<SteeringRecord>(`/runs/${run.runId}/messages`, "POST", { submission_id: pending.current.id, text });
      pending.current = null; return true;
    } catch { setError(true); return false; }
    finally { setSending(false); }
  }
  return { send, error, sending };
}
