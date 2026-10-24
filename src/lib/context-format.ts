import type { Locale } from "../i18n";

/** Compact token counts: `48.8K` above a thousand, plain digits below. */
export function compactTokens(value: number, locale: Locale): string {
  const safe = Number.isFinite(value) ? Math.max(0, value) : 0;
  if (safe < 1000) return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(safe);
  const scaled = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(safe / 1000);
  return `${scaled}K`;
}

export function usedPercent(used: number, window: number | null): number {
  if (!window || window <= 0) return 0;
  return Math.min(1, Math.max(0, used / window));
}

export function percentLabel(fraction: number, locale: Locale): string {
  const whole = Math.round(fraction * 100);
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(whole)}٪`;
}

/** `۳۸٪ · ۴۸٫۸K / ۱۲۸٫۰K زمینه استفاده شده` — the tooltip and the ring's label. */
export function ringLabel(
  used: number,
  window: number | null,
  locale: Locale,
  estimated: { used: boolean; window: boolean },
): string {
  const fraction = usedPercent(used, window);
  const prefix = estimated.used ? "~" : "";
  const windowPrefix = estimated.window ? "~" : "";
  const scale = window ? `${prefix}${compactTokens(used, locale)} / ${windowPrefix}${compactTokens(window, locale)}` : `${prefix}${compactTokens(used, locale)}`;
  return `${percentLabel(fraction, locale)} · ${scale}`;
}

/** Arc geometry: `r=14` in a `36×36` box, drawn from the top clockwise. */
export function arcDash(fraction: number, radius = 14): { dasharray: string; dashoffset: number } {
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(1, Math.max(0, fraction));
  return { dasharray: `${circumference} ${circumference}`, dashoffset: circumference * (1 - clamped) };
}

export function barShare(value: number, total: number): number {
  if (!total || total <= 0) return 0;
  return Math.min(1, Math.max(0, value / total));
}
