"use client";
import { useEffect, useRef, useState } from "react";
import type { ModelInput, Preset, ProviderRecord, RunRequest, RunResponse, Settings, WorkspaceState } from "./protocol";
import { connection } from "./desktop";
import { api } from "./api";
import { decodeSSE, subscribe } from "./sse";
import { useRun } from "../store/run";
import type { Locale } from "../i18n";

export function useSession() {
  const [ready, setReady] = useState(false), [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false), [testing, setTesting] = useState<string | null>(null);
  const [models, setModels] = useState<ProviderRecord[]>([]), [presets, setPresets] = useState<Preset[]>([]);
  const [settings, setSettings] = useState<Settings>({ locale: "fa", default_model: null });
  const [spaces, setSpaces] = useState<WorkspaceState>({ recent: [], selected: null, tasks: [] });
  const [model, setModel] = useState("");
  const [mode, setMode] = useState<RunRequest["mode"]>("ask");
  const [vaultOk, setVaultOk] = useState(true);
  const [workspaceError, setWorkspaceError] = useState(false);
  const active = useRef<AbortController | null>(null);
  const locale: Locale = settings.locale === "en" ? "en" : "fa";
  const workspace = spaces.selected ?? "";
  const branch = spaces.recent?.find(item => item.path === workspace)?.branch ?? null;
  const usableModel = models.some(provider => provider.id === model && provider.supports_tools && provider.probe?.status === "ok");
  async function refresh() {
    const [providers, workspaces] = await Promise.all([api<ProviderRecord[]>("/models"), api<WorkspaceState>("/workspaces")]);
    setModels(providers); setSpaces(workspaces);
  }
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
  }, [locale]);
  useEffect(() => {
    const controller = new AbortController();
    async function health() {
      if (!connection()?.baseUrl) { setFailed(true); return; }
      for (let attempt = 0; attempt < 120 && !controller.signal.aborted; attempt++) {
        try {
          await api("/health", "GET", undefined, controller.signal);
          const [saved, providers, options, workspaces] = await Promise.all([
            api<Settings>("/settings"), api<ProviderRecord[]>("/models"), api<Preset[]>("/presets"), api<WorkspaceState>("/workspaces"),
          ]);
          if (controller.signal.aborted) return;
          setSettings(saved); setModels(providers); setPresets(options); setSpaces(workspaces);
          setModel(saved.default_model ?? "");
          setVaultOk(await connection()!.vaultStatus()); setReady(true); return;
        } catch { if (controller.signal.aborted) return; }
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      if (!controller.signal.aborted) setFailed(true);
    }
    void health();
    return () => { controller.abort(); active.current?.abort(); };
  }, []);
  async function selectWorkspace(path: string) {
    try { setSpaces(await api<WorkspaceState>("/workspaces", "POST", { path })); setFailed(false); setWorkspaceError(false); }
    catch { setWorkspaceError(true); }
  }
  async function pickWorkspace() {
    try { const path = await connection()?.pickWorkspace(); if (path) await selectWorkspace(path); }
    catch { setWorkspaceError(true); }
  }
  async function changeSettings(value: Settings) {
    try { setSettings(await api<Settings>("/settings", "PUT", value)); setFailed(false); return true; }
    catch { setFailed(true); return false; }
  }
  async function setLocale(value: Locale) { await changeSettings({ ...settings, locale: value }); }
  async function makeDefault(id: string) {
    if (await changeSettings({ ...settings, default_model: id })) setModel(id);
  }
  async function testModel(id: string): Promise<ProviderRecord | null> {
    setTesting(id);
    const timer = setInterval(() => { void refresh().catch(() => undefined); }, 500);
    try { const result = await api<ProviderRecord>(`/models/${id}/test`, "POST"); await refresh(); return result; }
    catch { setFailed(true); return null; }
    finally { clearInterval(timer); setTesting(null); }
  }
  async function saveModel(value: ModelInput & { api_key?: string }): Promise<boolean> {
    try {
      const result = await connection()?.saveModel(value);
      if (!result?.ok) { setVaultOk(false); return false; }
      setVaultOk(true); await refresh(); return true;
    } catch { setVaultOk(false); return false; }
  }
  async function start(task: string) {
    const bridge = connection();
    if (!bridge || !ready || busy || !workspace || !usableModel) return;
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setFailed(false); useRun.getState().reset();
    try {
      const result = await api<RunResponse>("/runs", "POST", { task, workspace, model, mode }, controller.signal);
      await subscribe(bridge.baseUrl, bridge.token, result.run_id, useRun.getState().receive, controller.signal);
    } catch { if (!controller.signal.aborted) setFailed(true); }
    finally { setBusy(false); await refresh().catch(() => undefined); }
  }
  async function openTask(id: string) {
    if (busy) return;
    try {
      const bridge = connection()!;
      const response = await fetch(`${bridge.baseUrl}/tasks/${id}/events`, { headers: { Authorization: `Bearer ${bridge.token}` } });
      if (!response.ok || !response.body) throw new Error();
      useRun.getState().reset();
      for await (const event of decodeSSE(response.body)) useRun.getState().receive(event);
      const task = spaces.tasks?.find(item => item.id === id);
      if (task) { await selectWorkspace(task.workspace); setModel(task.model); setMode(task.mode ?? "ask"); }
      if (task?.status === "interrupted") useRun.setState({ status: "stopped" });
    } catch { setFailed(true); }
  }
  async function stop() {
    const id = useRun.getState().runId;
    if (!id) return;
    try { await api(`/runs/${id}/stop`, "POST"); } catch { setFailed(true); }
  }
  return { ready, failed, busy, testing, workspace, branch, spaces, models, presets, settings, model, mode, locale, vaultOk, usableModel, workspaceError,
    setModel, setMode, setLocale, makeDefault, saveModel, testModel, selectWorkspace, pickWorkspace, start, stop, openTask };
}
export type Session = ReturnType<typeof useSession>;
