import { useEffect, useState } from "react";
import { api } from "./api";
import { useInbox } from "./inbox";
import type { ApprovalRecord, PlanningSettings } from "./protocol";

export function usePlanningSettings(workspace: string) {
  const [value, setValue] = useState<PlanningSettings | null>(null), [error, setError] = useState(false);
  const [saving, setSaving] = useState(false), [approvalId, setApprovalId] = useState<string | null>(null);
  const records = useInbox(state => state.records);
  const approval = records.find(record => record.request.approval_id === approvalId);
  useEffect(() => {
    let live = true; setValue(null); setError(false);
    if (workspace) void api<PlanningSettings>(`/planning/settings?workspace=${encodeURIComponent(workspace)}`)
      .then(next => { if (live) setValue(next); }).catch(() => { if (live) setError(true); });
    return () => { live = false; };
  }, [workspace, approval?.status]);
  async function save() {
    if (!value || !workspace || saving) return;
    setSaving(true); setError(false);
    try {
      const record = await api<ApprovalRecord>(`/planning/settings?workspace=${encodeURIComponent(workspace)}`, "PUT", value);
      setApprovalId(record.request.approval_id); await useInbox.getState().refresh();
    } catch { setError(true); }
    finally { setSaving(false); }
  }
  return { value, setValue, error, saving, save, approval };
}
