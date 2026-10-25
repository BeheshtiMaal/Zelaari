"use client";
import { useCallback, useEffect, useState } from "react";
import { connection, reconnect } from "./desktop";
import { useRun } from "../store/run";

/**
 * Whether the engine is running, and how to bring it back.
 *
 * A restart is a new process on a new port with a new token, so this adopts the
 * connection the bridge returns before telling the caller to reopen the task it was
 * showing. Until then the card stays up: a half-restarted app is worse than a stopped one.
 */
export function useEngine(onRestored?: (runId: string) => void) {
  const [alive, setAlive] = useState(true);
  const [restarting, setRestarting] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const stop = connection()?.onEngineStatus(next => {
      setAlive(next);
      if (next) setFailed(false);
    });
    return () => { stop?.(); };
  }, []);
  const restart = useCallback(async () => {
    const bridge = connection();
    if (!bridge || restarting) return;
    const open = useRun.getState().runId;
    setRestarting(true); setFailed(false);
    try {
      const next = await bridge.restartEngine();
      if (!next) { setFailed(true); return; }
      reconnect(next);
      setAlive(true);
      if (open) onRestored?.(open);
    } catch { setFailed(true); }
    finally { setRestarting(false); }
  }, [restarting, onRestored]);
  return { alive, restarting, failed, restart };
}
