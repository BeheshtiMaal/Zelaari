import type { ApprovalDecision, ApprovalRequest } from "./protocol";

/** What the modal shows: one line naming the thing, one line naming the risk. */
export interface ApprovalView {
  tool: string;
  target: string;
  targetIsCommand: boolean;
  risk: "low" | "high";
  reasons: string[];
  reason: string;
}

export function approvalView(approval: ApprovalRequest): ApprovalView {
  const command = approval.command ?? null;
  return {
    tool: approval.tool,
    target: command ?? approval.path ?? "",
    targetIsCommand: command !== null,
    risk: approval.risk?.level ?? "low",
    reasons: approval.risk?.reasons ?? [],
    reason: approval.reason ?? "",
  };
}

export function decision(verdict: "approve" | "reject", reason?: string): ApprovalDecision {
  return verdict === "reject" && reason ? { decision: verdict, reason } : { decision: verdict };
}

/**
 * Enter approves and Esc rejects (R23). Anything else returns null so the caller can
 * ignore it; the modal is the only place this mapping exists.
 */
export function keyAction(key: string): "approve" | "reject" | null {
  if (key === "Enter") return "approve";
  if (key === "Escape") return "reject";
  return null;
}

/** A run that is waiting on a person is paused, not running and not finished. */
export function runLabel(status: string, hasApproval: boolean): "paused" | string {
  return hasApproval ? "paused" : status;
}
