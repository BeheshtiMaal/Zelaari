"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useRef, useState } from "react";
import { XIcon } from "@phosphor-icons/react/dist/csr/X";
import { canConfirm, confirmOutcome } from "../../lib/confirm";

/**
 * The one destructive dialog.
 *
 * It names exactly what is removed, and the destructive button does not exist until the
 * acknowledgement is ticked. Focus returns to whatever opened it, and a failed action keeps
 * the dialog open with the reason rather than closing as if it had worked.
 */
export function ConfirmDialog({ title, description, effects, acknowledge, confirmLabel, cancelLabel, busy, failed, errorLabel, close, onConfirm }: {
  title: string; description: string; effects: string[]; acknowledge: string; confirmLabel: string; cancelLabel: string;
  busy: boolean; failed: boolean; errorLabel: string; close(): void; onConfirm(): Promise<boolean>;
}) {
  const [checked, setChecked] = useState(false);
  const previous = useRef(document.activeElement as HTMLElement | null);
  const run = async () => { if (confirmOutcome(await onConfirm()) === "close") close(); };
  return <Dialog.Root open onOpenChange={open => { if (!open && !busy) close(); }}>
    <Dialog.Portal>
      <Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="confirm-dialog" data-testid="confirm-dialog"
        onCloseAutoFocus={event => { event.preventDefault(); if (previous.current?.isConnected) previous.current.focus(); }}
        onEscapeKeyDown={event => { if (busy) event.preventDefault(); }}>
        <div className="dialog-heading"><Dialog.Title>{title}</Dialog.Title>
          <Dialog.Close className="icon-button" disabled={busy} aria-label={cancelLabel}><XIcon size={20} /></Dialog.Close>
        </div>
        <Dialog.Description className="muted">{description}</Dialog.Description>
        <ul className="confirm-effects">{effects.map(line => <li key={line} dir="auto">{line}</li>)}</ul>
        <label className="confirm-ack"><input type="checkbox" checked={checked} disabled={busy} data-testid="confirm-acknowledge"
          onChange={event => setChecked(event.target.checked)} />{acknowledge}</label>
        {failed && <p className="error" role="alert" data-testid="confirm-error">{errorLabel}</p>}
        <div className="dialog-actions">
          <Dialog.Close className="light-button" disabled={busy}>{cancelLabel}</Dialog.Close>
          <button type="button" className="destructive" data-testid="confirm-action" disabled={!canConfirm(checked, busy)}
            onClick={() => void run()}>{confirmLabel}</button>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
