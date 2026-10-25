"use client";
import * as Dialog from "@radix-ui/react-dialog";
import type { ScheduleCopy } from "../../i18n/schedule";
import type { Schedule } from "../../lib/schedule";

/**
 * One confirmation that names the loss (D32's shape): the schedule goes, the runs it already
 * produced stay as tasks under the workspace, and the person is told both.
 */
export function DeleteSchedule({ schedule, copy, busy, onConfirm, close }: {
  schedule: Schedule; copy: ScheduleCopy; busy: boolean; onConfirm(): void; close(): void;
}) {
  return <Dialog.Root open onOpenChange={open => { if (!open) close(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="schedule-dialog narrow" data-testid="schedule-delete-dialog">
        <div className="dialog-heading">
          <Dialog.Title>{copy.deleteTitle}</Dialog.Title>
          <Dialog.Close className="icon-button" aria-label={copy.close}>×</Dialog.Close>
        </div>
        <Dialog.Description className="muted">
          <strong>{schedule.name}</strong> — {copy.deleteHint}
        </Dialog.Description>
        <div className="dialog-actions">
          <button type="button" onClick={close}>{copy.cancel}</button>
          <button type="button" className="danger-button" disabled={busy} onClick={onConfirm} data-testid="schedule-delete-confirm">
            {busy ? copy.deleting : copy.remove}
          </button>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
