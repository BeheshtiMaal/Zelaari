import { create } from "zustand";
import { api } from "./api";
import type { ApprovalDecision, ApprovalRecord, ApprovalRequest, ApprovalResolution, TaskRecord } from "./protocol";

export type ApprovalStatus = "pending" | "approved" | "rejected" | "cancelled" | "all";
export const recordKey = (request: ApprovalRequest) => `${request.run_id}:${request.approval_id}`;
export function pendingCount(records: ApprovalRecord[]) { return records.filter(record => record.status === "pending").length; }
export function waitingRunIds(records: ApprovalRecord[]) { return new Set(records.filter(record => record.status === "pending").map(record => record.request.run_id)); }
export function taskNeedsAttention(task: TaskRecord, records: ApprovalRecord[]) {
  return !!task.waiting_on?.length || records.some(record => record.status === "pending" && record.request.run_id === task.id);
}
export function filteredApprovals(records: ApprovalRecord[], status: ApprovalStatus) {
  return records.filter(record => status === "all" || record.status === status).sort((a, b) =>
    Date.parse(b.request.created_at ?? "") - Date.parse(a.request.created_at ?? ""));
}
export function suggestedGlob(request: ApprovalRequest): string | null {
  if (!["write_file", "edit_file"].includes(request.tool) || !request.path) return null;
  const path = request.path.replaceAll("\\", "/").replace(/^\//, "");
  if (path.startsWith(".harness/") || !path.includes("/")) return null;
  return path.slice(0, path.lastIndexOf("/")) + "/**";
}
export function decisionPath(request: ApprovalRequest) {
  return `/runs/${encodeURIComponent(request.run_id)}/interrupts/${encodeURIComponent(request.approval_id)}`;
}
interface InboxState {
  records: ApprovalRecord[]; failed: boolean;
  decisionError: string | null;
  startedRunId: string | null;
  refresh(): Promise<void>;
  decide(request: ApprovalRequest, decision: ApprovalDecision): Promise<void>;
  preview(request: ApprovalRequest, args?: Record<string, unknown>): Promise<ApprovalRequest>;
}
export const useInbox = create<InboxState>((set, get) => ({
  records: [], failed: false, decisionError: null, startedRunId: null,
  async refresh() {
    try { set({ records: await api<ApprovalRecord[]>("/approvals"), failed: false }); }
    catch { set({ failed: true }); }
  },
  async decide(request, decision) {
    set({ decisionError: null });
    try { const result = await api<ApprovalResolution>(decisionPath(request), "POST", decision); if (result.run_id) set({ startedRunId: result.run_id }); }
    catch (error) {
      await get().refresh();
      const record = get().records.find(record => recordKey(record.request) === recordKey(request));
      set({ decisionError: record?.result ?? "review_failed" });
      throw error;
    }
    await get().refresh();
  },
  async preview(request, args) {
    const preview = await api<ApprovalRequest>(decisionPath(request) + "/preview", "POST", { decision: "approve", ...(args ? { edited_args: args } : {}) });
    await get().refresh(); return preview;
  },
}));
