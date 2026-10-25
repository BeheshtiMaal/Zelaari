import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  APPEARANCE_KEY,
  BOOTSTRAP,
  DEFAULT_APPEARANCE,
  FONTS,
  FONT_SCALE,
  LOCALES,
  THEMES,
  activityView,
  appearanceAttributes,
  currentAppearance,
  fontScale,
  resolveTheme,
  segment,
  withAppearance,
} from "../../src/lib/appearance";

const css = readFileSync("src/app/globals.css", "utf8");

test("system follows the OS and an explicit theme never does", () => {
  assert.equal(resolveTheme("dark", true), "dark");
  assert.equal(resolveTheme("dark", false), "dark");
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("light", false), "light");
  assert.equal(resolveTheme("system", true), "dark");
  assert.equal(resolveTheme("system", false), "light");
});

test("the document only ever carries a resolved theme, never 'system'", () => {
  assert.deepEqual(appearanceAttributes("system", "large", true), { "data-theme": "dark", "data-font": "large" });
  assert.deepEqual(appearanceAttributes("system", "small", false), { "data-theme": "light", "data-font": "small" });
  for (const theme of THEMES) {
    for (const prefersDark of [true, false]) {
      assert.notEqual(appearanceAttributes(theme, "medium", prefersDark)["data-theme"], "system");
    }
  }
});

test("the segments are the mock's, in the mock's order", () => {
  assert.deepEqual(THEMES, ["dark", "light", "system"]);
  assert.deepEqual(FONTS, ["small", "medium", "large"]);
  assert.deepEqual(LOCALES, ["fa", "en"]);
  const themes = segment(THEMES, ["تیره", "روشن", "مثل سیستم"], "dark");
  assert.deepEqual(themes.map(option => option.label), ["تیره", "روشن", "مثل سیستم"]);
  assert.deepEqual(themes.map(option => option.pressed), [true, false, false]);
  const fonts = segment(FONTS, ["کوچک", "متوسط", "بزرگ"], "medium");
  assert.deepEqual(fonts.map(option => option.value), ["small", "medium", "large"]);
  assert.equal(fonts.filter(option => option.pressed).length, 1);
  assert.equal(fonts.find(option => option.pressed)?.label, "متوسط");
});

test("a missing label falls back to the stored value instead of an empty button", () => {
  assert.deepEqual(segment(["a", "b"], ["only one"], "b"), [
    { value: "a", label: "only one", pressed: false },
    { value: "b", label: "b", pressed: true },
  ]);
});

test("the font scale grows and the default is exactly one", () => {
  assert.equal(fontScale("medium"), 1);
  assert.ok(fontScale("small") < 1);
  assert.ok(fontScale("large") > 1);
  assert.deepEqual(Object.keys(FONT_SCALE), [...FONTS]);
});

test("every activity switch defaults to on, so a partial payload hides nothing", () => {
  assert.deepEqual(activityView(undefined), { show_thinking: true, keep_thinking_open: true, show_terminal: true });
  assert.deepEqual(activityView({}), { show_thinking: true, keep_thinking_open: true, show_terminal: true });
  assert.deepEqual(activityView({ show_terminal: false }), { show_thinking: true, keep_thinking_open: true, show_terminal: false });
  assert.deepEqual(activityView({ show_thinking: false, keep_thinking_open: false }), {
    show_thinking: false,
    keep_thinking_open: false,
    show_terminal: true,
  });
});

test("the stored preferences keep the mock's defaults for anything the engine did not send", () => {
  assert.deepEqual(currentAppearance({}), DEFAULT_APPEARANCE);
  assert.deepEqual(currentAppearance({ appearance: { theme: "light" } }), { ...DEFAULT_APPEARANCE, theme: "light" });
  assert.deepEqual(currentAppearance({ appearance: { show_thinking: false } }).show_thinking, false);
});

test("changing one preference keeps the others and the rest of the settings", () => {
  const before = { locale: "en" as const, default_model: "demo", appearance: { theme: "dark" as const, font: "large" as const } };
  const after = withAppearance(before, { theme: "light" });
  assert.notEqual(after, before);
  assert.equal(after.locale, "en");
  assert.equal(after.default_model, "demo");
  assert.equal(after.appearance?.theme, "light");
  assert.equal(after.appearance?.font, "large");
  assert.equal(after.appearance?.show_terminal, true);
  // The original is untouched: a rejected write has to be able to put it back.
  assert.equal(before.appearance.theme, "dark");
});

test("the pre-paint script reads the same key the hook writes", () => {
  assert.ok(BOOTSTRAP.includes(JSON.stringify(APPEARANCE_KEY)));
  assert.ok(BOOTSTRAP.startsWith("(function(){try{"));
  assert.ok(BOOTSTRAP.includes('setAttribute("data-theme"'));
  assert.ok(BOOTSTRAP.includes('setAttribute("data-font"'));
  assert.ok(BOOTSTRAP.includes('"rtl"'));
  assert.ok(BOOTSTRAP.includes("catch(e)"));
  // It runs inside the document head, so a stray close tag would break the page.
  assert.ok(!BOOTSTRAP.toLowerCase().includes("</script"));
});

test("the stylesheet answers all three font steps and the default scale", () => {
  for (const font of FONTS) {
    assert.match(css, new RegExp(`html\\[data-font="${font}"\\]\\s*\\{\\s*--fs-scale:`));
  }
  // The base size is a step like any other, and every step carries the preference.
  assert.match(css, /font-size:\s*var\(--fs-14\)/);
  assert.match(css, /--fs-14:\s*calc\(14px \* var\(--fs-scale, 1\)\)/);
  assert.ok(css.includes("--fs-scale: 1;"), "the medium step has to be exactly one");
});
