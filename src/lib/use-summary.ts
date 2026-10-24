import { useEffect, useState } from "react";
import { api } from "./api";
import type { RunSummary } from "./protocol";

/** Whether this run has a summary a new chat could start from. */
export function useRunSummary(runId: string | null, version = 0) {
  const [value, setValue] = useState<RunSummary | null>(null);
  useEffect(() => {
    let live = true;
    if (!runId) { setValue(null); return; }
    void api<RunSummary>(`/runs/${encodeURIComponent(runId)}/summary`)
      .then(next => { if (live) setValue(next); })
      .catch(() => { if (live) setValue(null); });
    return () => { live = false; };
  }, [runId, version]);
  return value;
}
