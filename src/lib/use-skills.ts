"use client";
import { useCallback, useEffect, useState } from "react";
import type {
  ApprovalRecord,
  MarketplaceCatalog,
  SkillDetail,
  SkillRecord,
  SkillsResponse,
} from "./protocol";
import { api } from "./api";
import { useInbox } from "./inbox";
import { draftValue, installPayload, type InstallKind, type SkillDraft } from "./skills";

const query = (workspace: string) => `?workspace=${encodeURIComponent(workspace)}`;

/**
 * The Skills tab: one read of the workspace, one selected detail, and four writes that
 * only ever produce an approval. Nothing here mutates a skill directly.
 */
export function useSkills(workspace: string) {
  const [data, setData] = useState<SkillsResponse | null>(null);
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [market, setMarket] = useState<MarketplaceCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [proposal, setProposal] = useState<ApprovalRecord | null>(null);

  const load = useCallback(async () => {
    if (!workspace) return;
    setBusy(true); setError(null);
    try { setData(await api<SkillsResponse>(`/skills${query(workspace)}`)); }
    catch { setError("error"); }
    finally { setBusy(false); }
  }, [workspace]);

  const read = useCallback(async (name: string | null) => {
    if (!workspace || !name) { setDetail(null); return; }
    try { setDetail(await api<SkillDetail>(`/skills/${encodeURIComponent(name)}${query(workspace)}`)); }
    catch { setDetail(null); setError("error"); }
  }, [workspace]);

  useEffect(() => { setSelected(null); setDetail(null); setProposal(null); setMarket(null); void load(); }, [load]);
  useEffect(() => { void read(selected); }, [read, selected]);

  const status = useInbox(state => proposal
    ? state.records.find(record => record.request.approval_id === proposal.request.approval_id)?.status
    : null);
  useEffect(() => {
    if (!status || status === "pending") return;
    setProposal(null);
    void load();
    void read(selected);
  }, [status, load, read, selected]);

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

  const skills: SkillRecord[] = data?.skills ?? [];
  const problems: SkillRecord[] = data?.problems ?? [];

  return {
    data, skills, problems, detail, selected, market, error, busy, proposal,
    select: (name: string | null) => setSelected(name),
    load, read,
    async toggle(skill: { name: string; enabled?: boolean }) {
      if (busy) return;
      setBusy(true); setError(null);
      try {
        await api<SkillRecord>(`/skills/enabled${query(workspace)}`, "PUT", {
          name: skill.name,
          enabled: !skill.enabled,
        });
        await load();
      } catch { setError("error"); }
      finally { setBusy(false); }
    },
    install: (kind: InstallKind, source: string) => propose(() => {
      const payload = installPayload(kind, source);
      return api<ApprovalRecord>(`/skills/install${query(workspace)}`, "POST", payload);
    }),
    create: (draft: SkillDraft) => propose(() =>
      api<ApprovalRecord>(`/skills/create${query(workspace)}`, "POST", draftValue(draft))),
    save: (draft: SkillDraft) => propose(() =>
      api<ApprovalRecord>(`/skills/${encodeURIComponent(draft.name)}${query(workspace)}`, "PUT", draftValue(draft))),
    remove: (name: string) => propose(() =>
      api<ApprovalRecord>(`/skills/${encodeURIComponent(name)}${query(workspace)}`, "DELETE")),
    async readMarket() {
      if (!workspace) return;
      setBusy(true); setError(null);
      try { setMarket(await api<MarketplaceCatalog>(`/skills/marketplace${query(workspace)}`)); }
      catch { setError("error"); }
      finally { setBusy(false); }
    },
    async setCatalog(url: string) {
      if (!workspace) return;
      setBusy(true); setError(null);
      try { setMarket(await api<MarketplaceCatalog>(`/skills/marketplace${query(workspace)}`, "PUT", { url })); }
      catch { setError("error"); }
      finally { setBusy(false); }
    },
  };
}

export type SkillsHub = ReturnType<typeof useSkills>;
