"use client";
import { useState } from "react";
import type { Locale } from "../../i18n";
import { approvalCopy } from "../../i18n/approvals";
import { recordKey, suggestedGlob, useInbox } from "../../lib/inbox";
import { useApprovalEditor } from "../../lib/use-approval-editor";
import type { ApprovalRecord } from "../../lib/protocol";
import { DiffView } from "./diff-view";
import { reviewShortcut } from "../../lib/approvals";

export function ApprovalCard({ record, locale, inline = false }: { record: ApprovalRecord; locale: Locale; inline?: boolean }) {
  const t = approvalCopy(locale), request = record.request, editor = useApprovalEditor(record);
  const [compact, setCompact] = useState(false);
  const pending = record.status === "pending", glob = suggestedGlob(request);
  if (inline && compact) return <section className="approval-card inline" data-testid="approval-card"><div className="approval-chips"><strong>{t.needsYou}</strong><span className={`risk-badge ${request.risk?.level ?? "low"}`}>{request.risk?.level === "high" ? t.high : t.low}</span></div><code dir="ltr">{request.tool} · {request.path ?? request.command}</code><div className="approval-actions"><button onClick={() => setCompact(false)}>{t.reviewOpen}</button><a href={`/approvals/?approval=${encodeURIComponent(recordKey(request))}`}>{t.open}</a></div></section>;
  return <section className={`approval-card ${inline ? "inline" : ""}`} tabIndex={0} data-testid="approval-card"
    aria-label={t.needsYou} onKeyDown={event => {
      if (!pending || editor.busy || editor.editing) return;
      const target = event.target as HTMLElement;
      const action = reviewShortcut(event.key, target.tagName, target.isContentEditable);
      if (action) { event.preventDefault(); void editor.decide(action); }
    }}>
    <div className="approval-chips"><span className="type-chip">{request.tool === "rules_update" ? t.rules : request.kind === "command" ? t.command : t.file}</span>
      <span className={`risk-badge ${request.risk?.level ?? "low"}`}>{request.risk?.level === "high" ? t.high : t.low}</span>
      {!pending && <span className="type-chip">{t[record.status ?? "pending"]}</span>}
      <span className="approval-source" dir="auto">{request.source_title}</span>
      {inline && <button onClick={() => setCompact(true)}>{t.collapse}</button>}
    </div>
    <h2>{inline ? t.needsYou : request.kind === "command" ? t.command : request.tool === "rules_update" ? t.rules : t.changeStart} {request.path && <code dir="ltr">{request.path}</code>} {!inline && request.kind !== "command" && request.tool !== "rules_update" ? t.changeEnd : ""}</h2>
    {inline && <code dir="ltr">{request.tool}{request.path ? ` · ${request.path}` : ""}</code>}
    {request.command && <pre className="command-preview" dir="ltr">{request.command}{request.args?.timeout ? `\n${request.args.timeout}s` : ""}</pre>}
    <div className="approval-explanation"><strong>{request.agent_reason ? t.reason : t.policy}</strong> {request.agent_reason ?? (request.policy_code === "rules_change" ? t.rulePolicy : t.policyRequired)}</div>
    {request.diff && <DiffView diff={request.diff} />}
    {request.diff && <p className="muted">{t.snapshot.split(".harness/snapshots")[0]}<bdi dir="ltr">.harness/snapshots</bdi>{t.snapshot.split(".harness/snapshots")[1]}</p>}
    {record.result && <div><strong>{t.result}</strong><pre dir="ltr" className="command-preview">{record.result}</pre></div>}
    {pending && <>
      {glob && <label className="allow-rule"><input type="checkbox" checked={editor.allow} disabled={editor.busy} onChange={event => editor.setAllow(event.target.checked)} /><span>{t.allow} <code dir="ltr">{glob}</code> {t.allowSuffix}</span></label>}
      {editor.allow && <p className="muted">{t.allowNote}</p>}
      {editor.editing && <label className="approval-input">{t.input}<textarea dir="ltr" rows={7} value={editor.input} onChange={event => editor.setInput(event.target.value)} /></label>}
      <label className="approval-input"><span className="sr-only">{t.rejection}</span><textarea rows={2} placeholder={t.rejection} aria-label={t.rejection} value={editor.reason} disabled={editor.busy} onChange={event => editor.setReason(event.target.value)} /></label>
      {editor.reviewed && <p className="success" role="status">{t.inputsChanged}</p>}
      {editor.error && <p className="error" role="alert">{t.error} <button onClick={() => void editor.preview()}>{t.refresh}</button></p>}
      <div className="approval-actions">
        {editor.editing ? <button className="approve" disabled={editor.busy} onClick={() => void editor.preview()}>{t.review}</button> : <button className="approve" data-testid="approval-approve" disabled={editor.busy} onClick={() => void editor.decide("approve")}>{editor.busy ? t.loading : t.approve}</button>}
        {request.tool !== "worktree_create" && <button disabled={editor.busy} onClick={() => editor.setEditing(!editor.editing)}>{t.edit}</button>}
        <button className="reject" data-testid="approval-reject" disabled={editor.busy || editor.editing} onClick={() => void editor.decide("reject")}>{t.reject}</button>
        {inline ? <a href={`/approvals/?approval=${encodeURIComponent(recordKey(request))}`}>{t.open}</a> : <span className="muted shortcuts" dir="ltr">{t.shortcuts}</span>}
      </div>
    </>}
    {record.answer?.reason && !pending && <p dir="auto">{record.answer.reason}</p>}
  </section>;
}

/** Model-composed cards can only reference an actual engine-owned record. */
export function RegisteredApprovalCard({ runId, approvalId }: { runId: string; approvalId: string }) {
  const record = useInbox(state => state.records.find(record => record.request.run_id === runId && record.request.approval_id === approvalId));
  if (!record) return null;
  const locale = typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "fa";
  return <ApprovalCard key={recordKey(record.request)} record={record} locale={locale} inline />;
}
