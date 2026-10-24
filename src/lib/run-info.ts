import type { Locale } from "../i18n";
import { compactTokens, percentLabel, usedPercent } from "./context-format";
import type { BudgetUpdated, HarnessEvent } from "./protocol";

/** The last budget the engine reported; the counters are cumulative per run. */
export function budgetOf(events: HarnessEvent[]): BudgetUpdated | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.type === "budget.updated") return event;
  }
  return null;
}

export interface Occupancy {
  /** `۳۸٪ · ۴۸٫۸K از ۱۲۸٫۰K` */
  text: string;
  fraction: number;
}

/** Context occupancy in the mock's wording; null when no window is known yet. */
export function occupancy(
  used: number,
  window: number | null,
  estimated: { used: boolean; window: boolean },
  locale: Locale,
  of: string,
): Occupancy | null {
  if (!window || window <= 0) return null;
  const prefix = estimated.used ? "~" : "", windowPrefix = estimated.window ? "~" : "";
  const fraction = usedPercent(used, window);
  return {
    text: `${percentLabel(fraction, locale)} · ${prefix}${compactTokens(used, locale)} ${of} ${windowPrefix}${compactTokens(window, locale)}`,
    fraction,
  };
}

export interface LimitRow {
  key: "steps" | "fixes";
  label: string;
  value: string;
}

/** `۱۱ از ۴۰` — real counters, or nothing at all when no budget was reported. */
export function limitRows(
  budget: BudgetUpdated | null,
  copy: { steps: string; fixes: string; of: string },
  locale: Locale,
): LimitRow[] {
  if (!budget) return [];
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  return [
    { key: "steps", label: copy.steps, value: `${number.format(budget.steps)} ${copy.of} ${number.format(budget.max_steps)}` },
    { key: "fixes", label: copy.fixes, value: `${number.format(budget.fix_attempts)} ${copy.of} ${number.format(budget.max_fix_attempts)}` },
  ];
}
