"use client";
import { useCallback, useEffect, useState } from "react";
import type {
  AgentDocument,
  AgentRecord,
  ApprovalRecord,
  ConnectorList,
  ConnectorStatus,
  CustomizeSettings,
  McpServerInput,
  MemoryDocument,
} from "./protocol";
import { api } from "./api";
import { useInbox } from "./inbox";

const query = (workspace: string) => `?workspace=${encodeURIComponent(workspace)}`;

function useProposal(workspace: string, reload: () => Promise<void> | void) {
  const [proposal, setProposal] = useState<ApprovalRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const status = useInbox(state => proposal
    ? state.records.find(record => record.request.approval_id === proposal.request.approval_id)?.status
    : null);
  useEffect(() => {
    if (!status || status === "pending") return;
    setProposal(null);
    void reload();
  }, [status, reload]);
  async function propose(call: () => Promise<ApprovalRecord>) {
    if (busy) return null;
    setBusy(true); setError(null);
    try {
      const record = await call();
      setProposal(record);
      await useInbox.getState().refresh();
      return record;
    } catch { setError("error"); return null; }
    finally { setBusy(false); }
  }
  return { proposal, error, busy, setError, propose, workspace };
}

export function useOverview(workspace: string) {
  const [counts, setCounts] = useState<CustomizeSettings | null>(null);
  const load = useCallback(async () => {
    if (!workspace) return;
    try { setCounts(await api<CustomizeSettings>(`/customize${query(workspace)}`)); }
    catch { setCounts(null); }
  }, [workspace]);
  useEffect(() => { void load(); }, [load]);
  return { counts, reload: load };
}

export function useMemory(workspace: string) {
  const [document, setDocument] = useState<MemoryDocument | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const value = await api<MemoryDocument>(`/memory${query(workspace)}`);
      setDocument(value);
      setDraft(value.content ?? "");
    } catch { setDocument(null); }
    finally { setLoading(false); }
  }, [workspace]);
  useEffect(() => { void load(); }, [load]);
  const saved = useProposal(workspace, load);
  async function save() {
    return saved.propose(() => api<ApprovalRecord>(`/memory${query(workspace)}`, "PUT", { content: draft }));
  }
  return { document, draft, setDraft, loading, load, save, ...saved };
}

export interface AgentDraft {
  name: string;
  description: string;
  instructions: string;
  tools: string[];
}

export const EMPTY_AGENT: AgentDraft = { name: "", description: "", instructions: "", tools: [] };

export function useAgents(workspace: string) {
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [document, setDocument] = useState<AgentDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!workspace) return;
    setBusy(true);
    try { setAgents(await api<AgentRecord[]>(`/agents${query(workspace)}`)); }
    catch { setAgents([]); }
    finally { setBusy(false); }
  }, [workspace]);
  const read = useCallback(async (name: string | null) => {
    if (!workspace || !name) { setDocument(null); return; }
    try { setDocument(await api<AgentDocument>(`/agents/${encodeURIComponent(name)}${query(workspace)}`)); }
    catch { setDocument(null); }
  }, [workspace]);
  useEffect(() => { setSelected(null); setDocument(null); void load(); }, [load]);
  useEffect(() => { void read(selected); }, [read, selected]);
  const saved = useProposal(workspace, async () => { await load(); await read(selected); });
  return {
    agents, selected, document, busy, load, saved,
    select: (name: string | null) => setSelected(name),
    create: (draft: AgentDraft) => saved.propose(() =>
      api<ApprovalRecord>(`/agents${query(workspace)}`, "POST", draft)),
    update: (draft: AgentDraft) => saved.propose(() =>
      api<ApprovalRecord>(`/agents/${encodeURIComponent(draft.name)}${query(workspace)}`, "PUT", draft)),
    remove: (name: string) => saved.propose(() =>
      api<ApprovalRecord>(`/agents/${encodeURIComponent(name)}${query(workspace)}`, "DELETE")),
  };
}

export function useConnectors(workspace: string) {
  const [servers, setServers] = useState<ConnectorStatus[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tested, setTested] = useState<ConnectorStatus | null>(null);
  const load = useCallback(async () => {
    if (!workspace) return;
    setBusy(true);
    try { setServers((await api<ConnectorList>(`/connectors${query(workspace)}`)).servers ?? []); }
    catch { setServers([]); }
    finally { setBusy(false); }
  }, [workspace]);
  useEffect(() => { setSelected(null); setTested(null); void load(); }, [load]);
  const saved = useProposal(workspace, load);
  async function test(name: string) {
    setBusy(true);
    try { setTested(await api<ConnectorStatus>(`/connectors/${encodeURIComponent(name)}/test${query(workspace)}`, "POST")); }
    catch { setTested(null); saved.setError("error"); }
    finally { setBusy(false); }
  }
  return {
    servers, selected, tested, busy, load, saved,
    select: (name: string | null) => { setSelected(name); setTested(null); },
    test,
    add: (server: McpServerInput) => saved.propose(() =>
      api<ApprovalRecord>(`/connectors${query(workspace)}`, "POST", server)),
    update: (server: McpServerInput) => saved.propose(() =>
      api<ApprovalRecord>(`/connectors/${encodeURIComponent(server.name)}${query(workspace)}`, "PUT", server)),
    remove: (name: string) => saved.propose(() =>
      api<ApprovalRecord>(`/connectors/${encodeURIComponent(name)}${query(workspace)}`, "DELETE")),
  };
}

export type ConnectorsHub = ReturnType<typeof useConnectors>;
