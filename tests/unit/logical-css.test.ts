import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, it } from "node:test";
import { BOOTSTRAP } from "../../src/lib/appearance";

/**
 * The layout has no left and no right (R15).
 *
 * A physical property is a bug that only shows in one language, so it is caught here rather
 * than in a screenshot of the other one. The same scan also covers the two things a person
 * needs from a mixed-direction screen: a direction on every code sample, and no positive
 * `tabindex`, which would take the tab order away from the document.
 */

const ROOT = process.cwd();
const CSS = readFileSync(resolve(ROOT, "src/app/globals.css"), "utf8");

const PHYSICAL_CSS = /(?:margin|padding|border)-(?:left|right)\b|(?:^|[^-a-z])left\s*:|(?:^|[^-a-z])right\s*:|text-align\s*:\s*(?:left|right)\b/gm;
const PHYSICAL_STYLE = /\b(?:margin|padding|border)(?:Left|Right)\b|\btextAlign\s*:\s*["'](?:left|right)["']|\b(?:left|right)\s*:/g;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap(name => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx$/.test(name) ? [path] : [];
  });
}

const TSX = sourceFiles(resolve(ROOT, "src"));

describe("the stylesheet", () => {
  it("never names a side", () => {
    assert.deepEqual([...CSS.matchAll(PHYSICAL_CSS)].map(match => match[0]), []);
  });

  it("positions and spaces with logical properties instead", () => {
    for (const property of ["margin-inline", "padding-inline", "inset-inline", "border-inline", "inline-size"]) {
      assert.ok(CSS.includes(property), `the stylesheet should use ${property}`);
    }
  });

  /**
   * `transform` has no logical form, so a dialog centred with `inset-inline-start: 50%` plus
   * `translate(-50%, -50%)` is correct in English and half a width off-screen in Persian. The
   * Phase 9b walkthrough found this on the schedule dialog, where it made Confirm unclickable;
   * every dialog that centres this way needs the mirrored rule.
   */
  it("mirrors the centring transform for a right-to-left document", () => {
    const centred = [...CSS.matchAll(/\.([a-z][a-z-]*-dialog)\s*\{[^}]*transform:\s*translate\(-50%,\s*-50%\)/g)];
    assert.ok(centred.length > 0, "there should be at least one centred dialog");
    for (const [, name] of centred) {
      const head = CSS.indexOf(`[dir="rtl"] .${name}`);
      assert.notEqual(head, -1, `${name} must be mirrored for RTL`);
      const open = CSS.indexOf("{", head), close = CSS.indexOf("}", open);
      assert.match(CSS.slice(open, close), /translate\(50%,\s*-50%\)/, `${name} must flip its horizontal shift`);
    }
  });
});

describe("the inline styles", () => {
  it("never name a side either", () => {
    const stray = TSX.flatMap(file => {
      const source = readFileSync(file, "utf8");
      return [...source.matchAll(/style=\{\{([^}]*)\}\}/g)]
        .flatMap(match => [...match[1].matchAll(PHYSICAL_STYLE)].map(hit => `${file}: ${hit[0]}`));
    });
    assert.deepEqual(stray, []);
  });

  it("are not used to set direction, which belongs on the element", () => {
    const stray = TSX.filter(file => /style=\{\{[^}]*direction\s*:/.test(readFileSync(file, "utf8")));
    assert.deepEqual(stray, []);
  });
});

describe("the document", () => {
  it("takes its language and direction from the stored locale before first paint", () => {
    assert.match(BOOTSTRAP, /r\.lang\s*=/, "the bootstrap must set lang");
    assert.match(BOOTSTRAP, /r\.dir\s*=/, "the bootstrap must set dir");
    assert.match(BOOTSTRAP, /rtl/, "and pick a direction, not just copy the locale");
    assert.match(BOOTSTRAP, /ltr/);
  });

  it("marks every code sample as left-to-right", () => {
    const stray = TSX.flatMap(file => readFileSync(file, "utf8").split("\n")
      .map((line, index) => ({ line, index }))
      .filter(({ line }) => line.includes("<code") && !line.includes('dir="ltr"'))
      .map(({ line, index }) => `${file}:${index + 1}: ${line.trim().slice(0, 120)}`));
    assert.deepEqual(stray, []);
  });

  it("leaves the tab order to the document", () => {
    const stray = TSX.flatMap(file => readFileSync(file, "utf8").split("\n")
      .map((line, index) => ({ line, index }))
      .filter(({ line }) => /tabIndex=\{?["']?[1-9]/.test(line))
      .map(({ line, index }) => `${file}:${index + 1}: ${line.trim().slice(0, 120)}`));
    assert.deepEqual(stray, []);
  });
});
