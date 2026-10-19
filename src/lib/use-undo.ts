"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { SnapshotEntry } from "./protocol";

/** Snapshot lookup and user-initiated undo for the selected workspace file. */
export function useUndo(workspace: string, path: string | undefined) {
  const [snapshot, setSnapshot] = useState<SnapshotEntry | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    setSnapshot(null); setFailed(false);
    if (workspace && path) void api<SnapshotEntry[]>(`/snapshots?workspace=${encodeURIComponent(workspace)}`)
      .then(entries => { if (live) setSnapshot(entries.find(entry => entry.path === path) ?? null); })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [workspace, path]);

  async function revert(): Promise<{ existed: boolean } | null> {
    if (!snapshot || busy) return null;
    setBusy(true); setFailed(false);
    try {
      await api(`/snapshots/${encodeURIComponent(snapshot.id)}/revert`, "POST", { workspace });
      const result = { existed: snapshot.existed };
      setSnapshot(null);
      return result;
    } catch { setFailed(true); return null; }
    finally { setBusy(false); }
  }
  return { available: snapshot !== null, busy, failed, revert };
}
