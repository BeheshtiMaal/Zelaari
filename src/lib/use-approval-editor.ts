"use client";
import { useRef, useState } from "react";
import type { ApprovalRecord } from "./protocol";
import { suggestedGlob, useInbox } from "./inbox";

export function useApprovalEditor(record: ApprovalRecord) {
  const [editing, setEditing] = useState(false), [input, setInput] = useState(JSON.stringify(record.request.args ?? {}, null, 2));
  const [reason, setReason] = useState(""), [allow, setAllow] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState(false), [reviewed, setReviewed] = useState(false);
  const lock = useRef(false);
  async function preview() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(false);
    try {
      const value: unknown = editing ? JSON.parse(input) : undefined;
      if (value !== undefined && (!value || typeof value !== "object" || Array.isArray(value))) throw new Error();
      await useInbox.getState().preview(record.request, value as Record<string, unknown> | undefined);
      setEditing(false); setReviewed(true);
    } catch { setError(true); }
    finally { lock.current = false; setBusy(false); }
  }
  async function decide(decision: "approve" | "reject") {
    if (lock.current || record.status !== "pending" || editing) return;
    lock.current = true; setBusy(true); setError(false);
    try {
      await useInbox.getState().decide(record.request, {
        decision, reason: reason || null, revision: record.request.revision ?? null,
        ...(allow && suggestedGlob(record.request) ? { allow_glob: suggestedGlob(record.request) } : {}),
      });
    } catch { setError(true); }
    finally { lock.current = false; setBusy(false); }
  }
  return { editing, setEditing, input, setInput, reason, setReason, allow, setAllow, busy, error, reviewed, preview, decide };
}
