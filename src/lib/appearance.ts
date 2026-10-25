import type { Appearance, Settings } from "./protocol";

export type Theme = "dark" | "light" | "system";
export type Font = "small" | "medium" | "large";
export type Locale = "fa" | "en";

/** Where the shell remembers appearance between launches, so the first paint is already themed. */
export const APPEARANCE_KEY = "codeharness.appearance";

/** The mock's order: dark first because dark is the default, and `system` last as the fallback. */
export const THEMES: readonly Theme[] = ["dark", "light", "system"];
export const FONTS: readonly Font[] = ["small", "medium", "large"];
export const LOCALES: readonly Locale[] = ["fa", "en"];

export const DEFAULT_APPEARANCE: Required<Appearance> = {
  theme: "dark",
  font: "medium",
  show_thinking: true,
  keep_thinking_open: true,
  show_terminal: true,
};

/** The root font-size multiplier each step of the scale applies. */
export const FONT_SCALE: Record<Font, number> = { small: 0.92, medium: 1, large: 1.12 };

export type ActivityView = Pick<Required<Appearance>, "show_thinking" | "keep_thinking_open" | "show_terminal">;

export function resolveTheme(theme: Theme, prefersDark: boolean): "dark" | "light" {
  return theme === "system" ? (prefersDark ? "dark" : "light") : theme;
}

export function fontScale(font: Font): number {
  return FONT_SCALE[font] ?? FONT_SCALE.medium;
}

/** The attributes the stylesheet switches on. `system` is resolved here, once, so CSS never guesses. */
export function appearanceAttributes(theme: Theme, font: Font, prefersDark: boolean): Record<string, string> {
  return { "data-theme": resolveTheme(theme, prefersDark), "data-font": font };
}

/** The stored preferences with the mock's defaults filled in for anything the engine did not send. */
export function currentAppearance(settings: Settings): Required<Appearance> {
  const value = settings.appearance ?? {};
  return {
    theme: value.theme ?? DEFAULT_APPEARANCE.theme,
    font: value.font ?? DEFAULT_APPEARANCE.font,
    show_thinking: value.show_thinking ?? DEFAULT_APPEARANCE.show_thinking,
    keep_thinking_open: value.keep_thinking_open ?? DEFAULT_APPEARANCE.keep_thinking_open,
    show_terminal: value.show_terminal ?? DEFAULT_APPEARANCE.show_terminal,
  };
}

/** Every switch defaults to on, so a missing or partial payload never hides the run's activity. */
export function activityView(appearance?: Appearance | null): ActivityView {
  const value = currentAppearance({ appearance: appearance ?? undefined });
  return {
    show_thinking: value.show_thinking,
    keep_thinking_open: value.keep_thinking_open,
    show_terminal: value.show_terminal,
  };
}

/** A partial appearance patch, keeping every other preference and the rest of the settings. */
export function withAppearance(settings: Settings, patch: Appearance): Settings {
  return { ...settings, appearance: { ...currentAppearance(settings), ...patch } };
}

/** Pairs ordered values with their labels; exactly one option is pressed, and it is the current one. */
export function segment<T extends string>(
  values: readonly T[],
  labels: readonly string[],
  current: string,
): { value: T; label: string; pressed: boolean }[] {
  return values.map((value, index) => ({ value, label: labels[index] ?? value, pressed: value === current }));
}

/**
 * Runs in the document head before the first paint. It reads the same key the hook writes and
 * applies it to `<html>`, so a light-theme or English user never sees a dark RTL flash.
 */
export const BOOTSTRAP = [
  "(function(){try{",
  `var a=JSON.parse(localStorage.getItem(${JSON.stringify(APPEARANCE_KEY)})||"null")||{};`,
  "var r=document.documentElement;",
  'var t=a.theme||"dark";',
  'var dark=t==="dark"||(t==="system"&&!(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches));',
  'r.setAttribute("data-theme",dark?"dark":"light");',
  'r.setAttribute("data-font",a.font||"medium");',
  'if(a.locale==="fa"||a.locale==="en"){r.lang=a.locale;r.dir=a.locale==="fa"?"rtl":"ltr";}',
  "}catch(e){}})();",
].join("");
