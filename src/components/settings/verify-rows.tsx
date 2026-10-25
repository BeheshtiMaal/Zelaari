"use client";
import { useState, type ReactNode } from "react";
import type { Locale } from "../../i18n";
import { bounded, localeDigits, parseDigits } from "../../lib/localised-number";

export function Row({ title, help, children }: { title: string; help?: string; children: ReactNode }) {
  return <div className="verify-row">
    <div className="verify-row-text"><strong>{title}</strong>{help && <span className="muted">{help}</span>}</div>
    <div className="verify-row-control">{children}</div>
  </div>;
}

export function Switch({ checked, label, testId, onChange }: { checked: boolean; label: string; testId: string; onChange(value: boolean): void }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} data-testid={testId}
    className="verify-switch" onClick={() => onChange(!checked)}><span aria-hidden="true" /></button>;
}

/** A segmented choice: the pressed option is the stored value, in the mock's order. */
export function Segment<T extends string>({ options, label, testId, onSelect }: {
  options: { value: T; label: string; pressed: boolean }[]; label: string; testId: string; onSelect(value: T): void;
}) {
  return <div className="language-segment" role="group" aria-label={label} data-testid={testId}>
    {options.map(option => <button key={option.value} type="button" aria-pressed={option.pressed}
      onClick={() => onSelect(option.value)}>{option.label}</button>)}
  </div>;
}

export function NumberField({ value, min, max, locale, label, testId, onChange }: {
  value: number; min: number; max: number; locale: Locale; label: string; testId: string; onChange(value: number): void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  return <input type="text" inputMode="numeric" className="verify-number" data-testid={testId} aria-label={label}
    value={draft ?? localeDigits(value, locale)}
    onChange={event => {
      const raw = event.target.value;
      setDraft(raw);
      const parsed = parseDigits(raw);
      if (parsed !== null) onChange(bounded(parsed, min, max, value));
    }}
    onBlur={() => setDraft(null)} />;
}

export function SaveBar({ saving, error, saved, onSave, copy }: {
  saving: boolean; error: boolean; saved: boolean; onSave(): void;
  copy: { save: string; saving: string; saved: string; error: string; approval: string };
}) {
  return <div className="verify-save">
    <button type="button" className="light-button" data-testid="verify-save" disabled={saving} onClick={onSave}>{saving ? copy.saving : copy.save}</button>
    {error && <p className="error" role="alert">{copy.error}</p>}
    {saved && <p className="muted" role="status">{copy.saved}</p>}
    <p className="muted verify-approval">{copy.approval}</p>
  </div>;
}
