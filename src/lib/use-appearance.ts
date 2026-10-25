"use client";
import { useEffect } from "react";
import type { Settings } from "./protocol";
import { APPEARANCE_KEY, DEFAULT_APPEARANCE, appearanceAttributes } from "./appearance";

const DARK = "(prefers-color-scheme: dark)";

/**
 * Applies the appearance preferences to `<html>` and remembers them for the next launch.
 *
 * The head script in `layout.tsx` already did this before the first paint; this effect keeps the
 * document in step afterwards, including while the OS switches between light and dark.
 */
export function useAppearance(settings: Settings) {
  const theme = settings.appearance?.theme ?? DEFAULT_APPEARANCE.theme;
  const font = settings.appearance?.font ?? DEFAULT_APPEARANCE.font;
  const locale = settings.locale === "en" ? "en" : "fa";
  useEffect(() => {
    const query = window.matchMedia(DARK);
    const apply = () => {
      const root = document.documentElement;
      for (const [name, value] of Object.entries(appearanceAttributes(theme, font, query.matches))) {
        root.setAttribute(name, value);
      }
    };
    apply();
    if (theme !== "system") return;
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, [theme, font]);
  useEffect(() => {
    try {
      localStorage.setItem(APPEARANCE_KEY, JSON.stringify({ theme, font, locale }));
    } catch {
      // A blocked store only costs the first paint of the next launch; the engine still has it.
    }
  }, [theme, font, locale]);
}
