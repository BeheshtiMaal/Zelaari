"use client";
import { useEffect, useRef, useState } from "react";
import type { ApprovalRequest, BranchList, ModelInput, Preset, ProviderRecord, RunRequest, RunResponse, Settings, WorkspaceState } from "./protocol";
import { connection } from "./desktop";
import { api, ApiError } from "./api";
import { decision } from "./approvals";
import { decodeSSE, subscribe } from "./sse";
import { useRun } from "../store/run";
import type { Locale } from "../i18n";

const NO_BRANCHES: BranchList = { git: false, current: null, branches: [] };

function pendingWorktreeApproval(error: unknown): ApprovalRequest | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const body = error.body as { approval?: ApprovalRequest } | null;
  return body?.approval ?? null;
}

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
  const [branches, setBranches] = useState<BranchList>(NO_BRANCHES);
  const [worktree, setWorktree] = useState(false);
  const [worktreeApproval, setWorktreeApproval] = useState<ApprovalRequest | null>(null);
  const [branchApproval, setBranchApproval] = useState<ApprovalRequest | null>(null);
  const [branchError, setBranchError] = useState<string | null>(null);
  const waitingBranch = useRef<string | null>(null);
  const waitingTask = useRef<string | null>(null);
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
  useEffect(() => {
    if (!workspace) { setBranches(NO_BRANCHES); setWorktree(false); return; }
    let live = true;
    void api<BranchList>(`/workspaces/branches?workspace=${encodeURIComponent(workspace)}`)
      .then(value => { if (live) setBranches(value); })
      .catch(() => { if (live) setBranches(NO_BRANCHES); });
    return () => { live = false; };
  }, [workspace]);
  async function selectWorkspace(path: string) {
    try { setSpaces(await api<WorkspaceState>("/workspaces", "POST", { path })); setFailed(false); setWorkspaceError(false); }
    catch { setWorkspaceError(true); }
  }
  async function pickWorkspace() {
    try { const path = await connection()?.pickWorkspace(); if (path) await selectWorkspace(path); }
    catch { setWorkspaceError(true); }
  }
  async function revealWorkspace() {
    if (!workspace) return;
    try { await connection()?.revealWorkspace(workspace); } catch { setFailed(true); }
  }
  async function switchBranch(name: string, approved = false) {
    if (!workspace || name === branch) return;
    setBranchError(null);
    try {
      await api("/workspaces/branch", "POST", { workspace, branch: name, mode, approved });
      await refresh();
      setBranches(await api<BranchList>(`/workspaces/branches?workspace=${encodeURIComponent(workspace)}`));
    } catch (error) {
      const pending = pendingWorktreeApproval(error);
      if (pending) { waitingBranch.current = name; setBranchApproval(pending); return; }
      const detail = error instanceof ApiError ? (error.body as { detail?: unknown } | null)?.detail : null;
      setBranchError(typeof detail === "string" ? detail : String(error));
    }
  }
  async function approveBranch() {
    const name = waitingBranch.current;
    waitingBranch.current = null; setBranchApproval(null);
    if (name) await switchBranch(name, true);
  }
  function rejectBranch() { waitingBranch.current = null; setBranchApproval(null); }
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
  async function start(task: string, approved = false) {
    const bridge = connection();
    if (!bridge || !ready || busy || !workspace || !usableModel) return;
    active.current?.abort();
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setFailed(false); useRun.getState().reset();
    const request: RunRequest = { task, workspace, model, mode, ...(worktree ? { worktree: true, worktree_approved: approved } : {}) };
    try {
      const result = await api<RunResponse>("/runs", "POST", request, controller.signal);
      await subscribe(bridge.baseUrl, bridge.token, result.run_id, useRun.getState().receive, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) return;
      // A worktree is gated before the run exists, so its approval arrives here rather
      // than as an approval.requested event on the stream.
      const pending = pendingWorktreeApproval(error);
      if (pending) { waitingTask.current = task; setWorktreeApproval(pending); return; }
      setFailed(true);
    }
    finally { setBusy(false); await refresh().catch(() => undefined); }
  }
  async function approveWorktree() {
    const task = waitingTask.current;
    setWorktreeApproval(null); waitingTask.current = null;
    if (task) await start(task, true);
  }
  function rejectWorktree() { setWorktreeApproval(null); waitingTask.current = null; }
  async function retryWithLongerTimeout(command: string) {
    // The engine refuses a longer timeout without a fresh approval, so this starts a
    // new run whose `run_command` call asks again. Phase 4 replaces it with a real
    // "retry this call with new arguments" channel.
    await start(`Run this command again with a timeout of 300 seconds: ${command}`);
  }
  async function resolveApproval(verdict: "approve" | "reject") {
    const state = useRun.getState(), pending = state.approval, id = state.runId;
    if (!pending || !id) return;
    try { await api(`/runs/${id}/interrupts/${pending.approval_id}`, "POST", decision(verdict)); }
    catch { setFailed(true); }
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
    branches, branchApproval, branchError, approveBranch, rejectBranch, worktree, worktreeApproval, setWorktree, setModel, setMode, setLocale, makeDefault, saveModel, testModel, selectWorkspace, pickWorkspace,
    revealWorkspace, switchBranch, start, approveWorktree, rejectWorktree, resolveApproval, retryWithLongerTimeout, stop, openTask };
}
export type Session = ReturnType<typeof useSession>;
