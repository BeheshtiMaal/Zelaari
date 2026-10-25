"use client";
import { useEffect, useState } from "react";
import type { Locale } from "../../i18n";
import { dictionary } from "../../i18n";

/**
 * The first thing a keyboard reaches, and the only way past the sidebar.
 *
 * It has to sit in the layout, before the navigation in document order, which is also why it
 * cannot receive the locale as a prop: the layout is rendered on the server before a session
 * exists. The bootstrap script has already put the locale on `<html>`, so this reads it back
 * after mount. Until then it renders in Persian, which is what a person who cannot see it yet
 * would have got anyway.
 */
export function SkipLink() {
  const [locale, setLocale] = useState<Locale>("fa");
  useEffect(() => { setLocale(document.documentElement.lang === "en" ? "en" : "fa"); }, []);
  return <a className="skip-link" href="#main" data-testid="skip-link">{dictionary(locale).skipToContent}</a>;
}
