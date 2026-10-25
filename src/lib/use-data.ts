"use client";
import { useCallback, useEffect, useState } from "react";
import type { DataSummary, DeletedRuns } from "./protocol";
import { api } from "./api";

export function useData(workspace: string) {
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [error, setError] = useState(false), [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setError(false);
    try {
      setSummary(await api<DataSummary>(`/data${workspace ? `?workspace=${encodeURIComponent(workspace)}` : ""}`));
    } catch { setError(true); }
  }, [workspace]);
  useEffect(() => { void load(); }, [load]);
  async function clearRuns(): Promise<DeletedRuns | null> {
    if (!workspace || busy) return null;
    setBusy(true);
    try {
      const result = await api<DeletedRuns>(`/data/runs?workspace=${encodeURIComponent(workspace)}`, "DELETE");
      await load();
      return result;
    } catch { setError(true); return null; }
    finally { setBusy(false); }
  }
  return { summary, error, busy, load, clearRuns };
}
