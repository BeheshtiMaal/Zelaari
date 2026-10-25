import assert from "node:assert/strict";
import { test } from "node:test";
import {
  authoredSkills,
  badgeOf,
  canEdit,
  draftFrom,
  draftValue,
  EMPTY_DRAFT,
  enabledCount,
  filterSkills,
  inCategory,
  installPayload,
  installedSkills,
  matchesQuery,
  scanOk,
  skillSource,
  tokenLabel,
} from "../../src/lib/skills";
import type { SkillDetail, SkillRecord } from "../../src/lib/protocol";

const grill: SkillRecord = {
  name: "grill-me", description: "Interview the person.", command: "/grill",
  category: "coding", source: "bundled", enabled: true, requires_approval: false,
  tokens: 40, scan: { status: "clean", findings: [], scripts: [] },
};
const search: SkillRecord = {
  name: "web-search", description: "Search the web.", command: "/search",
  category: "web", source: "bundled", enabled: false, requires_approval: true,
  tokens: 45, scan: { status: "clean", findings: [], scripts: [] },
};
const project: SkillRecord = {
  name: "read-framework-docs", description: "Read the docs.", category: "docs",
  source: "workspace", enabled: false, tokens: 55, scan: { status: "clean", findings: [], scripts: [] },
};
const blocked: SkillRecord = {
  name: "risky", description: "Does too much.", source: "user", enabled: false,
  scan: { status: "blocked", findings: ["rm_rf"], scripts: ["run.sh"] },
};

test("the badge states the most actionable fact", () => {
  assert.equal(badgeOf(grill), "ready");
  assert.equal(badgeOf(search), "needsApproval");
  assert.equal(badgeOf(project), "fromProject");
  assert.equal(badgeOf(blocked), "blocked");
  assert.equal(badgeOf({ ...grill, problem: "broken" }), "blocked");
  assert.equal(badgeOf({ ...grill, scan: { status: "flagged" } }), "broken");
});

test("a clean scan is the only clean scan", () => {
  assert.equal(scanOk(grill), true);
  assert.equal(scanOk({ ...grill, scan: undefined }), true);
  assert.equal(scanOk({ ...grill, scan: { status: "flagged" } }), false);
});

test("the token label is approximate and localised", () => {
  assert.equal(tokenLabel(40, "en"), "~40");
  assert.equal(tokenLabel(40, "fa"), "~۴۰");
  assert.equal(tokenLabel(undefined, "en"), "~0");
});

test("search matches the name or the description", () => {
  assert.equal(matchesQuery(grill, "grill"), true);
  assert.equal(matchesQuery(grill, "INTERVIEW"), true);
  assert.equal(matchesQuery(grill, "zzz"), false);
  assert.equal(matchesQuery(grill, "  "), true);
});

test("the category filter keeps other categories out", () => {
  assert.equal(inCategory(search, "web"), true);
  assert.equal(inCategory(search, "coding"), false);
  assert.equal(inCategory({ ...search, category: undefined }, "all"), true);
  assert.equal(inCategory({ ...search, category: undefined }, "coding"), false);
});

test("the installed list is everything available and the authored list is its project subset", () => {
  const all = [grill, search, project];
  assert.deepEqual(installedSkills(all).map(item => item.name), ["grill-me", "web-search", "read-framework-docs"]);
  assert.deepEqual(authoredSkills(all).map(item => item.name), ["read-framework-docs"]);
  assert.equal(enabledCount(all), 1);
});

test("filtering combines the query and the chip", () => {
  const all = [grill, search, project];
  assert.deepEqual(filterSkills(all, "search", "all").map(item => item.name), ["web-search"]);
  assert.deepEqual(filterSkills(all, "", "web").map(item => item.name), ["web-search"]);
  assert.deepEqual(filterSkills(all, "search", "coding"), []);
});

test("an install payload refuses an empty source", () => {
  assert.deepEqual(installPayload("folder", " C:/skills/one "), { kind: "folder", source: "C:/skills/one" });
  assert.throws(() => installPayload("zip", "   "));
});

test("an empty command field is sent as null", () => {
  assert.equal(draftValue(EMPTY_DRAFT).command, null);
  assert.equal(draftValue({ ...EMPTY_DRAFT, name: " a ", command: " /a " }).command, "/a");
  assert.equal(draftValue({ ...EMPTY_DRAFT, name: " a " }).name, "a");
});

const detail: SkillDetail = {
  name: "house-rules", description: "Project conventions.", body: "Run ruff.",
  command: "/rules", category: "coding", source: "workspace", enabled: true,
  requires_approval: false, tokens: 12, scan: { status: "clean" },
};

test("only a workspace skill can be edited", () => {
  assert.equal(canEdit(detail), true);
  assert.equal(canEdit({ ...detail, source: "bundled" }), false);
  assert.equal(canEdit({ ...detail, problem: "broken" }), false);
  assert.equal(canEdit(null), false);
});

test("the draft round-trips through the detail", () => {
  assert.deepEqual(draftFrom(detail), {
    name: "house-rules", description: "Project conventions.", body: "Run ruff.",
    command: "/rules", category: "coding",
  });
});

test("the detail shows the SKILL.md a person would read", () => {
  const text = skillSource(detail);
  assert.ok(text.startsWith("---\nname: house-rules\n"));
  assert.ok(text.includes("command: /rules"));
  assert.ok(text.includes("category: coding"));
  assert.ok(text.endsWith("Run ruff."));
  assert.ok(!text.includes("requires_approval"));
});
