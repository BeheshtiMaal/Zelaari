import type { Locale } from "../i18n";

/** The locale the document was rendered in. `<html lang>` is the only source of truth. */
export function currentLocale(): Locale {
  return typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "fa";
}
