import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";
import { appearanceAttributes, resolveTheme } from "../../src/lib/appearance";

/**
 * The stylesheet is the design system, so these tests read it as data.
 *
 * They are deliberately strict about three things a reviewer cannot check by eye in
 * both themes at once: that the two palettes describe the same roles, that no rule
 * names a colour of its own, and that the text still passes WCAG AA against the
 * surface it is actually drawn on.
 */

const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");

interface Block {
  from: number;
  to: number;
  body: string;
}

function blocks(selector: string): Block[] {
  const found: Block[] = [];
  let search = 0;
  for (;;) {
    const head = css.indexOf(selector + " {", search);
    if (head === -1) return found;
    const open = css.indexOf("{", head), from = open + 1;
    let depth = 0;
    for (let index = open; index < css.length; index += 1) {
      if (css[index] === "{") depth += 1;
      else if (css[index] === "}") {
        depth -= 1;
        if (depth === 0) {
          found.push({ from, to: index, body: css.slice(from, index) });
          search = index + 1;
          break;
        }
      }
    }
    if (depth !== 0) throw new Error(`Unbalanced block for ${selector}`);
  }
}

function tokens(source: string): Map<string, string> {
  const found = new Map<string, string>();
  for (const match of source.matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) found.set(match[1], match[2].trim());
  return found;
}

/** `:root` appears twice — the palette and the type scale — and the browser merges them. */
function merged(selector: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const block of blocks(selector)) for (const [name, value] of tokens(block.body)) out.set(name, value);
  return out;
}

const dark = merged(":root");
const light = merged('[data-theme="light"]');

/** The colour roles only: the type scale lives in a second `:root` block and is theme-free. */
const darkRoles = tokens(blocks(":root")[0].body);
const lightRoles = tokens(blocks('[data-theme="light"]')[0].body);

/** Everything except the palette blocks: the rules that must not name a colour. */
const paletteBlocks = [...blocks(":root"), ...blocks('[data-theme="light"]')]
  .sort((left, right) => right.from - left.from);
const rules = paletteBlocks.reduce((text, block) => text.slice(0, block.from) + text.slice(block.to), css);

function channel(value: number): number {
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const full = value.length === 3 ? [...value].map(letter => letter + letter).join("") : value;
  const [red, green, blue] = [0, 2, 4].map(index => channel(parseInt(full.slice(index, index + 2), 16) / 255));
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(foreground: string, background: string): number {
  const [high, low] = [luminance(foreground), luminance(background)].sort((left, right) => right - left);
  return (high + 0.05) / (low + 0.05);
}

function colour(palette: Map<string, string>, name: string): string {
  const value = palette.get(name);
  assert.ok(value, `${name} must be defined`);
  assert.match(value, /^#[0-9A-Fa-f]{6}$/, `${name} must be a plain hex colour, got ${value}`);
  return value;
}

/**
 * The pairs that matter, and the surface each one is actually drawn on.
 *
 * 4.5:1 is WCAG AA for body text. 3:1 is WCAG AA for the boundary of an active
 * control: an input whose edge cannot be seen is an input that cannot be found.
 * Decorative separators (`--border`) are not listed on purpose — they carry no
 * meaning on their own, and forcing them to 3:1 would make every card shout.
 */
const PAIRS: { foreground: string; background: string; minimum: number; why: string }[] = [
  { foreground: "--text", background: "--bg-surface", minimum: 4.5, why: "body text on the main surface" },
  { foreground: "--text", background: "--bg-card", minimum: 4.5, why: "body text on a card" },
  { foreground: "--text", background: "--bg-frame", minimum: 4.5, why: "body text on the frame" },
  { foreground: "--text", background: "--bg-raised", minimum: 4.5, why: "text on a raised chip" },
  { foreground: "--text", background: "--bg-selected-chip", minimum: 4.5, why: "the pressed option in a segment" },
  { foreground: "--text-soft", background: "--bg-card", minimum: 4.5, why: "secondary labels and nav items" },
  { foreground: "--text-muted", background: "--bg-card", minimum: 4.5, why: "muted help text" },
  { foreground: "--text-muted", background: "--bg-raised", minimum: 4.5, why: "chip labels" },
  { foreground: "--text-dim", background: "--bg-card", minimum: 4.5, why: "timestamps and captions" },
  { foreground: "--text-code", background: "--bg-terminal", minimum: 4.5, why: "command output" },
  { foreground: "--text-thinking", background: "--bg-thinking", minimum: 4.5, why: "the thinking panel" },
  { foreground: "--text-on-accent", background: "--accent", minimum: 4.5, why: "the label on an accent button" },
  { foreground: "--text-inverse", background: "--bg-inverse", minimum: 4.5, why: "the light button" },
  { foreground: "--accent-text", background: "--bg-card", minimum: 4.5, why: "a link on a card" },
  { foreground: "--ok-text", background: "--ok-bg", minimum: 4.5, why: "a success badge" },
  { foreground: "--warn-text", background: "--warn-bg", minimum: 4.5, why: "a warning badge" },
  { foreground: "--danger-text", background: "--danger-bg", minimum: 4.5, why: "a rejected badge" },
  { foreground: "--danger", background: "--bg-card", minimum: 4.5, why: "destructive text on a card" },
  { foreground: "--info-text", background: "--info-bg", minimum: 4.5, why: "an informational badge" },
  { foreground: "--notice-text", background: "--notice", minimum: 4.5, why: "the unread count" },
  { foreground: "--border-input", background: "--bg-card", minimum: 3, why: "an input edge on a card" },
  { foreground: "--border-button", background: "--bg-card", minimum: 3, why: "a secondary button edge" },
  { foreground: "--accent", background: "--bg-card", minimum: 3, why: "the selected border" },
  { foreground: "--accent-bright", background: "--bg-surface", minimum: 3, why: "the focus ring" },
];

describe("the two palettes", () => {
  it("are both present", () => {
    assert.ok(darkRoles.size > 20, "the dark palette must define the roles");
    assert.equal(lightRoles.size, darkRoles.size, "the light palette must define every role the dark one does");
  });

  it("define exactly the same role names", () => {
    assert.deepEqual([...lightRoles.keys()].sort(), [...darkRoles.keys()].sort());
  });

  it("put the light block after :root, because equal specificity is decided by order", () => {
    const root = blocks(":root")[0];
    const theme = blocks('[data-theme="light"]')[0];
    assert.ok(theme.from > root.from, "the light palette must come later in the file");
  });

  it("declare the colour scheme each palette is, so native controls follow", () => {
    assert.match(blocks(":root")[0].body, /color-scheme:\s*dark/);
    assert.match(blocks('[data-theme="light"]')[0].body, /color-scheme:\s*light/);
  });
});

describe("the rules", () => {
  it("never name a colour of their own", () => {
    const named = [...rules.matchAll(/#[0-9A-Fa-f]{3,8}\b|\brgba?\(|\bhsla?\(/g)].map(match => match[0]);
    assert.deepEqual(named, [], "every colour must come from a token");
  });

  it("only use tokens that are defined somewhere", () => {
    const defined = new Set([...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map(match => match[1]));
    const used = new Set([...rules.matchAll(/var\((--[a-z0-9-]+)/g)].map(match => match[1]));
    const missing = [...used].filter(name => !defined.has(name)).sort();
    assert.deepEqual(missing, []);
  });

  it("never write a raw font size", () => {
    assert.deepEqual([...rules.matchAll(/font-size:\s*[0-9.]+px/g)].map(match => match[0]), []);
  });

  it("size text only through the scale, so the font preference reaches every string", () => {
    const sizes = [...rules.matchAll(/font-size:\s*([^;}]+)/g)].map(match => match[1].trim());
    const offScale = sizes.filter(value => !value.startsWith("var(--fs-") && value !== "inherit");
    assert.deepEqual(offScale, []);
  });

  it("define every scale step as a multiple of the preference", () => {
    const scale = [...css.matchAll(/--fs-[0-9-]+:\s*([^;]+);/g)].map(match => match[1].trim());
    assert.ok(scale.length >= 10);
    for (const value of scale) assert.match(value, /^calc\([0-9.]+px \* var\(--fs-scale, 1\)\)$/);
  });
});

describe("contrast", () => {
  for (const [name, palette] of [["dark", dark], ["light", light]] as const) {
    it(`meets WCAG AA in the ${name} palette`, () => {
      const failures = PAIRS.map(pair => {
        const ratio = contrast(colour(palette, pair.foreground), colour(palette, pair.background));
        return { ...pair, ratio: Math.round(ratio * 100) / 100 };
      }).filter(pair => pair.ratio < pair.minimum);
      assert.deepEqual(failures, [], failures.map(pair => `${pair.why}: ${pair.ratio} < ${pair.minimum}`).join("; "));
    });
  }

  it("keeps the two palettes genuinely different", () => {
    const shared = [...dark.keys()].filter(name => name !== "--text-on-accent" && dark.get(name) === light.get(name));
    assert.deepEqual(shared, [], "a token that is the same in both themes is a token that does not belong to a theme");
  });
});

describe("the theme preference", () => {
  it("resolves system against the operating system, never stores it", () => {
    assert.equal(resolveTheme("system", true), "dark");
    assert.equal(resolveTheme("system", false), "light");
    assert.equal(resolveTheme("light", true), "light");
    assert.equal(resolveTheme("dark", false), "dark");
  });

  it("reaches the document as the attribute the palettes switch on", () => {
    assert.deepEqual(appearanceAttributes("system", "large", false), { "data-theme": "light", "data-font": "large" });
  });
});
