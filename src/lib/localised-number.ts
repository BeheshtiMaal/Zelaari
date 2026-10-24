import type { Locale } from "../i18n";

const PERSIAN = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC = "٠١٢٣٤٥٦٧٨٩";

/** Show a number in the reader's digits, without grouping separators. */
export function localeDigits(value: number | string, locale: Locale): string {
  const text = String(value);
  if (locale === "en") return text;
  return text.replace(/[0-9]/g, digit => PERSIAN[Number(digit)]);
}

/** Read a field that may hold Persian, Arabic or ASCII digits. */
export function parseDigits(text: string): number | null {
  const normalised = text
    .trim()
    .replace(/[۰-۹]/g, digit => String(PERSIAN.indexOf(digit)))
    .replace(/[٠-٩]/g, digit => String(ARABIC.indexOf(digit)));
  if (!/^-?\d+$/.test(normalised)) return null;
  return Number(normalised);
}

export function bounded(value: number | null, low: number, high: number, fallback: number): number {
  if (value === null || !Number.isFinite(value)) return fallback;
  return Math.min(high, Math.max(low, Math.round(value)));
}
