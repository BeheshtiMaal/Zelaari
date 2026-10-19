"use client";
import { useCallback, useEffect, useState } from "react";
import type { ApprovalRecord, Rule, RulesFile, RulesResponse } from "./protocol";
import { api } from "./api";
import { useInbox } from "./inbox";

export interface RuleRow { tool: string; glob: string; action: Rule["action"] }
export function rulesRows(value: RulesFile): RuleRow[] {
  return Object.entries(value.tools ?? {}).flatMap(([tool, rules]) => rules.map(rule => ({ tool, glob: rule.glob ?? "*", action: rule.action })));
}
export function rulesValue(mode: RulesFile["mode"], rows: RuleRow[]): RulesFile {
  const tools: NonNullable<RulesFile["tools"]> = {};
  for (const row of rows) {
    if (!row.tool.trim() || !row.glob.trim()) throw new Error("Empty rule");
    (tools[row.tool.trim()] ??= []).push({ glob: row.glob.trim(), action: row.action });
  }
  return { version: 1, mode, tools };
}
export function useRules(workspace: string) {
  const [mode, setMode] = useState<RulesFile["mode"]>("ask"), [rows, setRows] = useState<RuleRow[]>([]);
  const [effective, setEffective] = useState<RulesResponse | null>(null), [error, setError] = useState(false), [busy, setBusy] = useState(false);
  const [proposal, setProposal] = useState<ApprovalRecord | null>(null);
  const load = useCallback(async () => {
    if (!workspace) return;
    setBusy(true); setError(false);
    try {
      const value = await api<RulesResponse>(`/rules?workspace=${encodeURIComponent(workspace)}`);
      setEffective(value); setMode(value.rules?.mode ?? value.mode); setRows(rulesRows(value.rules ?? { mode: value.mode }));
    } catch { setError(true); }
    finally { setBusy(false); }
  }, [workspace]);
  useEffect(() => { setProposal(null); void load(); }, [load]);
  const status = useInbox(state => proposal ? state.records.find(record => record.request.approval_id === proposal.request.approval_id)?.status : null);
  useEffect(() => { if (status && status !== "pending") { setProposal(null); void load(); } }, [status, load]);
  function update(index: number, value: Partial<RuleRow>) { setRows(rows => rows.map((row, at) => at === index ? { ...row, ...value } : row)); }
  async function save() {
    if (busy) return;
    setBusy(true); setError(false);
    try {
      setProposal(await api<ApprovalRecord>(`/rules?workspace=${encodeURIComponent(workspace)}`, "PUT", rulesValue(mode, rows)));
      await useInbox.getState().refresh();
    } catch { setError(true); }
    finally { setBusy(false); }
  }
  return { mode, setMode, rows, setRows, effective, error, busy, proposal, update, save, load };
}
