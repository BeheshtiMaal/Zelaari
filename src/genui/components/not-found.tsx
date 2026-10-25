"use client";
import { genuiCopy } from "../../i18n/genui";
import { currentLocale } from "../../lib/locale";

/** The honest empty answer when a rendered component names an id the open run never produced. */
export function GenUiNotFound({ what }: { what: string }) {
  const locale = currentLocale(), t = genuiCopy(locale);
  return <p className="genui-missing" data-testid="genui-not-found" role="status">
    <strong>{what} · {t.notFound}</strong>
    <span className="muted">{t.notFoundHelp}</span>
  </p>;
}
