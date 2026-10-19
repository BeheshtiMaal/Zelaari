"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useRef } from "react";
import type { Dictionary } from "../i18n";
import { approvalView, keyAction } from "../lib/approvals";
import type { ApprovalRequest } from "../lib/protocol";

/**
 * The temporary Phase 3 approval surface (R23).
 *
 * One approval at a time, Approve and Reject only, Enter approves and Esc rejects.
 * Radix owns focus containment and the accessible name, so the dialog is usable by
 * keyboard and by screen reader without extra work here.
 */
export function ApprovalModal({ approval, t, onApprove, onReject }: {
  t: Dictionary; approval: ApprovalRequest; onApprove(): void; onReject(): void;
}) {
  const view = approvalView(approval);
  const approveButton = useRef<HTMLButtonElement>(null);
  return <Dialog.Root open>
    <Dialog.Portal>
      <Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="model-dialog approval-dialog" data-testid="approval-modal"
        onOpenAutoFocus={event => { event.preventDefault(); approveButton.current?.focus(); }}
        onEscapeKeyDown={event => { event.preventDefault(); onReject(); }}
        onKeyDown={event => {
          // A focused button already handles Enter; intercepting it here would reject
          // or approve the wrong way round depending on which button has focus.
          if ((event.target as HTMLElement).tagName === "BUTTON") return;
          const action = keyAction(event.key);
          if (!action) return;
          event.preventDefault();
          if (action === "approve") onApprove(); else onReject();
        }}>
        <div className="dialog-heading">
          <Dialog.Title>{t.approvalTitle}</Dialog.Title>
          <span className={`risk-badge ${view.risk}`} data-testid="risk-badge">{view.risk === "high" ? t.riskHigh : t.riskLow}</span>
        </div>
        <Dialog.Description className="approval-reason">{view.reason}</Dialog.Description>
        <dl className="approval-fields">
          <div><dt>{t.approvalTool}</dt><dd dir="ltr">{view.tool}</dd></div>
          <div><dt>{view.targetIsCommand ? t.approvalCommand : t.approvalPath}</dt>
            <dd dir="ltr" className="approval-target" data-testid="approval-target">{view.target || "—"}</dd></div>
        </dl>
        {view.reasons.length > 0 && <ul className="approval-reasons" aria-label={t.approvalRisks}>
          {view.reasons.map(reason => <li key={reason}>{reason}</li>)}
        </ul>}
        <p className="approval-note">{t.approvalPaused}</p>
        <div className="dialog-actions">
          <button type="button" className="danger-outline" data-testid="approval-reject" onClick={onReject}>{t.reject}</button>
          <button type="button" className="light-button" ref={approveButton} data-testid="approval-approve" onClick={onApprove}>{t.approve}</button>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
