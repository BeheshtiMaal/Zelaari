import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { describe, it } from "node:test";
import { dictionary } from "../../src/i18n";

/**
 * Two dictionaries, one shape (R16).
 *
 * Every copy module exports a `(locale) => object` selector, so the test discovers them
 * instead of listing them: a new module is covered the day it is written. The rules are the
 * ones a person would notice — a missing sentence, a placeholder that vanished in one
 * language, Latin digits in Persian.
 */

const I18N = resolve(process.cwd(), "src/i18n");

interface Copy { name: string; fa: unknown; en: unknown }

const selectorsIn = (file: string): string[] =>
  [...readFileSync(resolve(I18N, file), "utf8").matchAll(/export const (\w+)\s*=\s*\(locale: Locale\)/g)].map(match => match[1]);

const copies: Copy[] = [];
for (const file of readdirSync(I18N).filter(name => name.endsWith(".ts") && name !== "index.ts")) {
  const names = selectorsIn(file);
  if (!names.length) continue;
  const module = await import(pathToFileURL(resolve(I18N, file)).href) as Record<string, (locale: "fa" | "en") => unknown>;
  for (const name of names) copies.push({ name: `${file} · ${name}`, fa: module[name]("fa"), en: module[name]("en") });
}
copies.push({ name: "fa.ts · dictionary", fa: dictionary("fa"), en: dictionary("en") });

interface Leaf { path: string; value: string }

function leaves(value: unknown, path = "", out: Leaf[] = []): Leaf[] {
  if (typeof value === "string") out.push({ path, value });
  else if (Array.isArray(value)) value.forEach((item, index) => leaves(item, `${path}[${index}]`, out));
  else if (value && typeof value === "object") for (const [key, child] of Object.entries(value)) leaves(child, path ? `${path}.${key}` : key, out);
  return out;
}

/** The keys and their kinds, with array length kept, and nothing of the text. */
function shape(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(shape);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(key => [key, shape((value as Record<string, unknown>)[key])]));
  return typeof value;
}

const PERSIAN = /[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
const ASCII_DIGIT = /[0-9]/;
const placeholders = (text: string): string[] => [...text.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort();

describe("the dictionaries", () => {
  it("are all reachable, so the test is not passing over nothing", () => {
    assert.ok(copies.length >= 10, `found ${copies.length} copy modules`);
    assert.ok(copies.every(copy => leaves(copy.fa).length > 0), "a module with no strings is a module the test cannot check");
  });

  it("describe the same keys and the same kinds in both languages", () => {
    for (const copy of copies) assert.deepEqual(shape(copy.fa), shape(copy.en), `${copy.name} diverges`);
  });

  it("never ship an empty sentence", () => {
    const empty = copies.flatMap(copy => [
      ...leaves(copy.fa).filter(leaf => !leaf.value.trim()).map(leaf => `fa ${copy.name} ${leaf.path}`),
      ...leaves(copy.en).filter(leaf => !leaf.value.trim()).map(leaf => `en ${copy.name} ${leaf.path}`),
    ]);
    assert.deepEqual(empty, []);
  });

  it("keep the same placeholders on both sides", () => {
    const mismatched = copies.flatMap(copy => {
      const english = new Map(leaves(copy.en).map(leaf => [leaf.path, placeholders(leaf.value)]));
      return leaves(copy.fa)
        .filter(leaf => JSON.stringify(placeholders(leaf.value)) !== JSON.stringify(english.get(leaf.path)))
        .map(leaf => `${copy.name} ${leaf.path}: ${JSON.stringify(placeholders(leaf.value))} vs ${JSON.stringify(english.get(leaf.path))}`);
    });
    assert.deepEqual(mismatched, []);
  });

  it("keep Persian letters out of the English dictionary", () => {
    // The language name is the one string a person has to see in its own script.
    const allowed = new Set(["فارسی"]);
    const stray = copies.flatMap(copy => leaves(copy.en).filter(leaf => PERSIAN.test(leaf.value) && !allowed.has(leaf.value)).map(leaf => `${copy.name} ${leaf.path}: ${leaf.value}`));
    assert.deepEqual(stray, []);
  });

  it("write Persian copy with Persian digits", () => {
    const latin = copies.flatMap(copy => leaves(copy.fa).filter(leaf => ASCII_DIGIT.test(leaf.value)).map(leaf => `${copy.name} ${leaf.path}: ${leaf.value}`));
    assert.deepEqual(latin, []);
  });
});

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap(name => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(name) ? [path] : [];
  });
}

describe("the components", () => {
  it("read every user-visible string from a dictionary", () => {
    // A literal here is a sentence no one can translate, so the scan allows none of them.
    const files = [...sourceFiles(resolve(process.cwd(), "src/components")), ...sourceFiles(resolve(process.cwd(), "src/app"))];
    assert.ok(files.length > 40, `scanned ${files.length} files`);
    const stray = files.flatMap(file => readFileSync(file, "utf8").split("\n")
      .map((line, index) => ({ line, index }))
      .filter(({ line }) => PERSIAN.test(line))
      .map(({ line, index }) => `${file}:${index + 1}: ${line.trim()}`));
    assert.deepEqual(stray, []);
  });
});
