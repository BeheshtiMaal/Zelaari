"use client";
import { useEffect, useRef, useState } from "react";
import type { RunRequest, RunResponse } from "./protocol";
import { connection } from "./desktop";
import { subscribe } from "./sse";
import { useRun } from "../store/run";

export function useSession() {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [workspace, setWorkspace] = useState("");
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function health() {
      const bridge = connection();
      if (!bridge?.baseUrl) { setFailed(true); return; }
      for (let attempt = 0; attempt < 60 && !controller.signal.aborted; attempt++) {
        try {
          const response = await fetch(`${bridge.baseUrl}/health`, {
            headers: { Authorization: `Bearer ${bridge.token}` }, signal: controller.signal,
          });
          if (response.ok) { setReady(true); return; }
        } catch { if (controller.signal.aborted) return; }
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      if (!controller.signal.aborted) setFailed(true);
    }
    void health();
    return () => { controller.abort(); active.current?.abort(); };
  }, []);
  async function pickWorkspace() {
    const selected = await connection()?.pickWorkspace();
    if (selected) setWorkspace(selected);
  }
  async function start(task: string, model: RunRequest["model"]) {
    const bridge = connection();
    if (!bridge || !ready || busy || !workspace) return;
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setFailed(false); useRun.getState().reset();
    try {
      const body: RunRequest = { task, workspace, model };
      const response = await fetch(`${bridge.baseUrl}/runs`, {
        method: "POST", headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body), signal: controller.signal,
      });
      if (!response.ok) throw new Error("Run unavailable");
      const result = await response.json() as RunResponse;
      await subscribe(bridge.baseUrl, bridge.token, result.run_id, useRun.getState().receive, controller.signal);
    } catch { if (!controller.signal.aborted) setFailed(true); }
    finally { setBusy(false); }
  }
  async function stop() {
    const bridge = connection(), runId = useRun.getState().runId;
    if (!bridge || !runId) return;
    try {
      const response = await fetch(`${bridge.baseUrl}/runs/${runId}/stop`, {
        method: "POST", headers: { Authorization: `Bearer ${bridge.token}` },
      });
      if (!response.ok) setFailed(true);
    } catch { setFailed(true); }
  }
  return { ready, failed, workspace, busy, pickWorkspace, start, stop };
}
