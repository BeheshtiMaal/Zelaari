"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { RunFile, RunFileList } from "./protocol";

/**
 * The files a run changed, read from the engine's snapshots. `FileTree` renders this and
 * never a path list the model supplied, so the tree cannot claim work that never happened.
 */
export function useRunFiles(runId: string | null) {
  const [files, setFiles] = useState<RunFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!runId) { setFiles([]); setFailed(false); return; }
    let live = true;
    setLoading(true); setFailed(false);
    api<RunFileList>(`/runs/${encodeURIComponent(runId)}/files`)
      .then(result => { if (live) setFiles(result.files ?? []); })
      .catch(() => { if (live) { setFiles([]); setFailed(true); } })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [runId]);
  return { files, loading, failed };
}
