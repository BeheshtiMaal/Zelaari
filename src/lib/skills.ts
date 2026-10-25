import type { SkillDetail, SkillRecord } from "./protocol";
import { localeDigits } from "./localised-number";
import type { Locale } from "../i18n";

export type CategoryFilter = "all" | "coding" | "tests" | "web" | "docs";
export type Badge = "ready" | "needsApproval" | "fromProject" | "broken" | "blocked";

export const CATEGORIES: CategoryFilter[] = ["all", "coding", "tests", "web", "docs"];

/** The chip a card shows. One badge only: the most actionable fact wins. */
export function badgeOf(skill: SkillRecord): Badge {
  if (skill.problem || skill.scan?.status === "blocked") return "blocked";
  if (skill.scan?.status === "flagged") return "broken";
  if (skill.source === "workspace") return "fromProject";
  if (skill.requires_approval) return "needsApproval";
  return "ready";
}

export function scanOk(skill: SkillRecord): boolean {
  return (skill.scan?.status ?? "clean") === "clean";
}

/** `~40 tokens`: the cost of the summary line, marked approximate like everywhere else. */
export function tokenLabel(tokens: number | undefined, locale: Locale): string {
  return `~${localeDigits(tokens ?? 0, locale)}`;
}

export function matchesQuery(skill: SkillRecord, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return true;
  return `${skill.name} ${skill.description}`.toLocaleLowerCase().includes(needle);
}

export function inCategory(skill: SkillRecord, category: CategoryFilter): boolean {
  return category === "all" || (skill.category ?? "other") === category;
}

export function filterSkills(
  skills: SkillRecord[],
  query: string,
  category: CategoryFilter,
): SkillRecord[] {
  return skills.filter(skill => matchesQuery(skill, query) && inCategory(skill, category));
}

/**
 * `Installed` is everything this workspace can use: bundled, user and project.
 *
 * An install from a folder or a ZIP lands in the project's own skills root, so a filter
 * that excluded that root would hide the skill the person just approved. `Made by me` is
 * the narrower view over the same list, not its complement.
 */
export function installedSkills(skills: SkillRecord[]): SkillRecord[] {
  return skills;
}

export function authoredSkills(skills: SkillRecord[]): SkillRecord[] {
  return skills.filter(skill => skill.source === "workspace");
}

export function enabledCount(skills: SkillRecord[]): number {
  return skills.filter(skill => skill.enabled).length;
}

export type InstallKind = "folder" | "zip" | "git";

export interface InstallPayload {
  kind: InstallKind;
  source: string;
}

export function installPayload(kind: InstallKind, source: string): InstallPayload {
  const trimmed = source.trim();
  if (!trimmed) throw new Error("A source is required");
  return { kind, source: trimmed };
}

export interface SkillDraft {
  name: string;
  description: string;
  body: string;
  command: string;
  category: Exclude<CategoryFilter, "all">;
}

export const EMPTY_DRAFT: SkillDraft = {
  name: "",
  description: "",
  body: "",
  command: "",
  category: "coding",
};

/** A command is optional; an empty field must not become `command: ""`. */
export function draftValue(draft: SkillDraft) {
  return {
    name: draft.name.trim(),
    description: draft.description.trim(),
    body: draft.body,
    command: draft.command.trim() || null,
    category: draft.category,
  };
}

export function draftFrom(detail: SkillDetail): SkillDraft {
  return {
    name: detail.name,
    description: detail.description,
    body: detail.body ?? "",
    command: detail.command ?? "",
    category: (detail.category ?? "other") as SkillDraft["category"],
  };
}

export function canEdit(detail: SkillDetail | null): boolean {
  return detail !== null && detail.source === "workspace" && !detail.problem;
}

/** The SKILL.md a person will read in the detail panel, frontmatter included. */
export function skillSource(detail: SkillDetail): string {
  const lines = ["---", `name: ${detail.name}`, `description: ${detail.description}`];
  if (detail.command) lines.push(`command: ${detail.command}`);
  if (detail.category && detail.category !== "other") lines.push(`category: ${detail.category}`);
  if (detail.requires_approval) lines.push("requires_approval: true");
  lines.push("---", "", detail.body ?? "");
  return lines.join("\n");
}
