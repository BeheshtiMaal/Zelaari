"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useRef, useState } from "react";
import { SparkleIcon } from "@phosphor-icons/react/dist/csr/Sparkle";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import { FolderSimpleIcon } from "@phosphor-icons/react/dist/csr/FolderSimple";
import type { Locale } from "../../i18n";
import type { ScheduleCopy } from "../../i18n/schedule";
import {
  draftProblem,
  draftToInput,
  effectiveMode,
  type ScheduleDraft,
  type ScheduleMode,
} from "../../lib/schedule";
import type { ScheduleInput } from "../../lib/protocol";

const MODES: ScheduleMode[] = ["read-only", "ask", "auto"];

/**
 * Add and edit in one dialog.
 *
 * Two permission controls, and the stricter one wins — the effective mode is shown as it
 * changes, because a person choosing "full access" should see what that resolves to before
 * they press Confirm, not after the first unattended run.
 */
export function ScheduleDialog({ copy, locale, draft: initial, editing, workspaces, busy, error, onSave, close }: {
  copy: ScheduleCopy; locale: Locale; draft: ScheduleDraft; editing: boolean;
  workspaces: { path: string; name: string }[]; busy: boolean; error: string | null;
  onSave(value: ScheduleInput): Promise<boolean>; close(): void;
}) {
  const [draft, setDraft] = useState<ScheduleDraft>(initial);
  const nameField = useRef<HTMLInputElement>(null);
  const set = <K extends keyof ScheduleDraft>(key: K, value: ScheduleDraft[K]) =>
    setDraft(current => ({ ...current, [key]: value }));
  const problem = draftProblem(draft, copy);
  const effective = effectiveMode(draft.mode, draft.ceiling);
  return <Dialog.Root open onOpenChange={open => { if (!open) close(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="schedule-dialog" data-testid="schedule-dialog" aria-describedby={undefined}
        onOpenAutoFocus={event => { event.preventDefault(); nameField.current?.focus(); }}>
        <div className="dialog-heading">
          <Dialog.Title>{editing ? copy.editTitle : copy.addTitle}</Dialog.Title>
          <Dialog.Close className="icon-button" aria-label={copy.close}>×</Dialog.Close>
        </div>
        <form onSubmit={event => { event.preventDefault(); if (!problem) void onSave(draftToInput(draft)); }}>
          <fieldset disabled={busy}>
            <label>{copy.name}
              <input required ref={nameField} data-testid="schedule-name" value={draft.name}
                placeholder={copy.namePlaceholder} onChange={event => set("name", event.target.value)} />
            </label>

            <div className="prompt-box">
              <textarea required rows={4} data-testid="schedule-prompt" value={draft.prompt}
                placeholder={copy.promptPlaceholder} onChange={event => set("prompt", event.target.value)} />
              <div className="prompt-box-tools">
                <button type="button" className="icon-button" disabled title={copy.improveSoon}
                  aria-label={copy.improve} data-testid="schedule-improve"><SparkleIcon size={20} /></button>
                <label className={`chip mode-${draft.mode}`}>
                  <ShieldCheckIcon size={16} />
                  <span className="sr-only">{copy.mode}</span>
                  <select data-testid="schedule-mode" value={draft.mode}
                    onChange={event => set("mode", event.target.value as ScheduleMode)}>
                    {MODES.map(item => <option key={item} value={item}>{copy.modes[item]}</option>)}
                  </select>
                </label>
              </div>
            </div>

            <div className="dialog-row">
              <label>{copy.workspace}
                <select data-testid="schedule-workspace" value={draft.workspace}
                  onChange={event => set("workspace", event.target.value)}>
                  {workspaces.every(item => item.path !== draft.workspace) && draft.workspace &&
                    <option value={draft.workspace}>{draft.workspace}</option>}
                  {workspaces.map(item => <option key={item.path} value={item.path}>{item.name}</option>)}
                </select>
              </label>
              <label>{copy.ceiling}
                <span className={`chip ceiling-${draft.ceiling}`}>
                  <FolderSimpleIcon size={16} />
                  <select data-testid="schedule-ceiling" value={draft.ceiling}
                    onChange={event => set("ceiling", event.target.value as ScheduleDraft["ceiling"])}>
                    <option value="report">{copy.ceilings.report}</option>
                    <option value="full">{copy.ceilings.full}</option>
                  </select>
                </span>
              </label>
            </div>

            {draft.ceiling === "full" && <p className="danger-note" role="note" data-testid="schedule-full-warning">{copy.fullWarning}</p>}
            <p className="muted" data-testid="schedule-effective">{copy.effective.replace("{mode}", copy.modes[effective])}</p>

            <div className="dialog-row">
              <label>{copy.repeat}
                <select data-testid="schedule-repeat" value={draft.repeat}
                  onChange={event => set("repeat", event.target.value as ScheduleDraft["repeat"])}>
                  <option value="daily">{copy.repeats.daily}</option>
                  <option value="weekly">{copy.repeats.weekly}</option>
                </select>
              </label>
              {draft.repeat === "weekly" && <label>{copy.weekday}
                <select data-testid="schedule-weekday" value={draft.weekday}
                  onChange={event => set("weekday", Number(event.target.value))}>
                  {copy.weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
                </select>
              </label>}
              <label>{copy.time}
                <input type="time" required dir="ltr" data-testid="schedule-time" value={draft.time}
                  onChange={event => set("time", event.target.value)} />
              </label>
              <label>{copy.validity}
                <select data-testid="schedule-validity" value={draft.validUntil === "" ? "forever" : "until"}
                  onChange={event => set("validUntil", event.target.value === "forever" ? "" : localDay())}>
                  <option value="forever">{copy.validities.forever}</option>
                  <option value="until">{copy.validities.until}</option>
                </select>
              </label>
              {draft.validUntil !== "" && <label>{copy.untilDate}
                <input type="date" required dir="ltr" data-testid="schedule-until" value={draft.validUntil}
                  onChange={event => set("validUntil", event.target.value)} />
              </label>}
            </div>
          </fieldset>

          {error && <p className="error" role="alert">{error}</p>}
          {problem && <p className="muted" data-testid="schedule-problem">{problem}</p>}
          <div className="dialog-actions">
            <button type="button" onClick={close}>{copy.cancel}</button>
            <button className="light-button" type="submit" data-testid="schedule-confirm" disabled={busy || problem !== null}>
              {busy ? copy.saving : copy.confirm}
            </button>
          </div>
        </form>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

function localDay(): string {
  const at = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
}
