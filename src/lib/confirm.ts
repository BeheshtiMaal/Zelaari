import type { Locale } from "../i18n";
import { fillText } from "./errors";
import type { DataSummary } from "./protocol";

export type ConfirmKind = "runs" | "keys";

export interface ConfirmFacts {
  runs: number;
  tasks: number;
  bytes: number;
  keys: number;
  workspace: string;
  harness: string;
}

const UNITS: Record<Locale, readonly string[]> = {
  fa: ["بایت", "کیلوبایت", "مگابایت", "گیگابایت"],
  en: ["B", "KB", "MB", "GB"],
};

/** Sizes in the person's own units and digits; the card never shows a raw byte count. */
export function formatBytes(bytes: number, locale: Locale): string {
  const units = UNITS[locale];
  let value = Math.max(0, bytes), unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const rounded = unit === 0 ? Math.round(value) : Math.round(value * 10) / 10;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(rounded)} ${units[unit]}`;
}

/** Everything the two confirm dialogs name. Missing data reads as zero, never as "some". */
export function confirmFacts(summary: DataSummary | null, workspace: string): ConfirmFacts {
  const entry = summary?.workspaces?.find(item => item.path === workspace) ?? summary?.workspaces?.[0];
  return {
    runs: entry?.runs ?? 0,
    tasks: entry?.tasks ?? 0,
    bytes: (entry?.run_bytes ?? 0) + (entry?.checkpoints_bytes ?? 0),
    keys: summary?.keys ?? 0,
    workspace: entry?.path ?? workspace,
    harness: entry?.harness ?? "",
  };
}

/**
 * The run sentence the card and the dialog share.
 *
 * `{size}` is already text with its own unit, so this cannot go through the number
 * interpolation: `fill` would read "1.5 KB" as a number and print NaN.
 */
export function describeRuns(template: string, facts: ConfirmFacts, locale: Locale): string {
  const count = new Intl.NumberFormat(locale);
  return fillText(template, {
    runs: count.format(facts.runs),
    size: formatBytes(facts.bytes, locale),
    tasks: count.format(facts.tasks),
  });
}

export function describeKeys(template: string, facts: ConfirmFacts, locale: Locale): string {
  return fillText(template, { keys: new Intl.NumberFormat(locale).format(facts.keys) });
}

/** The checkbox is the gate: without it the destructive button does not exist. */
export function canConfirm(acknowledged: boolean, busy: boolean): boolean {
  return acknowledged && !busy;
}

/** The dialog stays open and says why when the action fails; it never closes on failure. */
export function confirmOutcome(ok: boolean): "close" | "stay" {
  return ok ? "close" : "stay";
}
