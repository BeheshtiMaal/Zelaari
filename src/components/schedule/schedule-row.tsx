"use client";
import * as Popover from "@radix-ui/react-popover";
import { useState } from "react";
import { ClockIcon } from "@phosphor-icons/react/dist/csr/Clock";
import { DotsThreeIcon } from "@phosphor-icons/react/dist/csr/DotsThree";
import type { Locale } from "../../i18n";
import type { ScheduleCopy } from "../../i18n/schedule";
import {
  formatTime,
  isMissed,
  lastResultLabel,
  recurrenceLabel,
  type Schedule,
} from "../../lib/schedule";

/**
 * One schedule.
 *
 * The row is the whole state of that schedule: what it does, how it is allowed to do it,
 * what happened last, and the switch that stops it. A missed occurrence grows a second line
 * with the two answers a person actually has — run it now, or skip it.
 */
export function ScheduleRow({ schedule, pending, now, locale, copy, busy, onToggle, onEdit, onRunNow, onSkip, onDelete }: {
  schedule: Schedule; pending: number; now: string; locale: Locale; copy: ScheduleCopy; busy: boolean;
  onToggle(enabled: boolean): void; onEdit(): void; onRunNow(): void; onSkip(): void; onDelete(): void;
}) {
  const [menu, setMenu] = useState(false);
  const result = lastResultLabel(schedule, pending, now, copy, locale);
  const missed = isMissed(schedule);
  return <div className={`schedule-row ${schedule.enabled ? "" : "paused"}`} data-testid={`schedule-row-${schedule.id}`}>
    <span className={`schedule-row-icon ${schedule.enabled ? "on" : ""}`} aria-hidden="true"><ClockIcon size={22} /></span>
    <div className="schedule-row-main">
      <strong>{schedule.name}</strong>
      <small>
        <span dir="ltr">{schedule.workspace.split(/[\\/]/).filter(Boolean).pop() ?? schedule.workspace}</span>
        {" · "}
        {recurrenceLabel(schedule, copy, locale)}
      </small>
    </div>
    <span className={`type-chip mode-${schedule.mode}`} data-testid={`schedule-mode-${schedule.id}`}>
      {copy.modes[schedule.mode]}
    </span>
    <span className={`schedule-result ${result.tone}`} data-testid={`schedule-result-${schedule.id}`}>{result.text}</span>
    <button type="button" role="switch" aria-checked={schedule.enabled} className={`switch ${schedule.enabled ? "on" : ""}`}
      aria-label={copy.switchLabel.replace("{name}", schedule.name)} disabled={busy}
      data-testid={`schedule-switch-${schedule.id}`} onClick={() => onToggle(!schedule.enabled)}>
      <span />
    </button>
    <Popover.Root open={menu} onOpenChange={setMenu}>
      <Popover.Trigger asChild>
        <button type="button" className="row-more" aria-label={copy.more} data-testid={`schedule-more-${schedule.id}`}>
          <DotsThreeIcon size={20} weight="bold" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className="row-menu" align="end" sideOffset={6}>
          <button type="button" onClick={() => { setMenu(false); onEdit(); }} data-testid={`schedule-edit-${schedule.id}`}>{copy.edit}</button>
          <button type="button" onClick={() => { setMenu(false); onRunNow(); }} data-testid={`schedule-run-${schedule.id}`}>{copy.runNow}</button>
          <button type="button" className="danger" onClick={() => { setMenu(false); onDelete(); }} data-testid={`schedule-delete-${schedule.id}`}>{copy.remove}</button>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
    {missed && <div className="schedule-missed" data-testid={`schedule-missed-${schedule.id}`}>
      <p>{copy.missedHint.replace("{time}", formatTime(schedule.time, locale))}</p>
      <button type="button" className="light-button" disabled={busy} onClick={onRunNow} data-testid={`schedule-missed-run-${schedule.id}`}>{copy.runNow}</button>
      <button type="button" disabled={busy} onClick={onSkip} data-testid={`schedule-missed-skip-${schedule.id}`}>{copy.skip}</button>
    </div>}
  </div>;
}
