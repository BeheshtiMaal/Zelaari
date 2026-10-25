import type { RulesResponse } from "./protocol";

export type Decision = "allow" | "ask" | "deny";
export type PermissionMode = "read-only" | "ask" | "auto";

/** The mock's order, and the order the composer offers. */
export const MODES: readonly PermissionMode[] = ["read-only", "ask", "auto"];

const RANK: Record<Decision, number> = { allow: 0, ask: 1, deny: 2 };

/**
 * The conditions the engine always asks about, in the order the screen shows them: the mock's
 * three first, then the two it does not draw (Decision 10). The engine reports five; showing
 * three would tell the person that MCP calls and long timeouts run unattended in Auto.
 */
export const LOCKED_ORDER = ["storage", "web", "commands", "mcp", "timeout", "other"] as const;
export type LockedKey = (typeof LOCKED_ORDER)[number];
export const KNOWN_LOCKED: readonly LockedKey[] = ["storage", "web", "commands", "mcp", "timeout"];

/** Engine strings are English and stable, but an unknown one must still show up, locked. */
export function lockedKey(text: string): LockedKey {
  const value = text.toLowerCase();
  if (value.includes(".harness")) return "storage";
  if (value.includes("web")) return "web";
  if (value.includes("mcp")) return "mcp";
  if (value.includes("timeout")) return "timeout";
  if (value.includes("command")) return "commands";
  return "other";
}

export interface LockedRow { key: LockedKey; text: string }

/**
 * The locked list, never editable. When the engine's list cannot be read the answer is still a
 * list: every known condition, locked, which over-states the boundary rather than under-stating
 * it. `assumed` lets the screen say so instead of pretending it read the engine.
 */
export function lockedRows(alwaysAsk?: string[] | null): { rows: LockedRow[]; assumed: boolean } {
  const values = Array.isArray(alwaysAsk) ? alwaysAsk.filter(text => typeof text === "string" && text.trim()) : [];
  if (!values.length) return { rows: KNOWN_LOCKED.map(key => ({ key, text: "" })), assumed: true };
  const rows = values.map(text => ({ key: lockedKey(text), text }));
  return { rows: rows.sort((left, right) => LOCKED_ORDER.indexOf(left.key) - LOCKED_ORDER.indexOf(right.key)), assumed: false };
}

export interface RuleView { tool: string; globs: string[]; action: Decision }

function strictest(actions: Decision[]): Decision {
  return actions.reduce<Decision>((worst, action) => RANK[action] > RANK[worst] ? action : worst, "allow");
}

function decision(value: string | undefined): Decision {
  return value === "allow" || value === "deny" ? value : "ask";
}

/** The rules the workspace actually wrote, one row per tool, strictest decision first. */
export function explicitRows(response?: RulesResponse | null): RuleView[] {
  return Object.entries(response?.tools ?? {})
    .map(([tool, rules]) => ({
      tool,
      globs: rules.map(rule => rule.glob || "*"),
      action: strictest(rules.map(rule => decision(rule.action))),
    }))
    .sort((left, right) => left.tool.localeCompare(right.tool));
}

/** The mode's ceiling per category, which is what applies when the workspace wrote no rule. */
export function defaultRows(response?: RulesResponse | null): RuleView[] {
  return Object.entries(response?.defaults ?? {}).map(([tool, action]) => ({
    tool,
    globs: ["*"],
    action: decision(action),
  }));
}

/** The effective grid: what the workspace wrote, or the mode's defaults when it wrote nothing. */
export function ruleRows(response?: RulesResponse | null): { rows: RuleView[]; fromDefaults: boolean } {
  const explicit = explicitRows(response);
  return explicit.length ? { rows: explicit, fromDefaults: false } : { rows: defaultRows(response), fromDefaults: true };
}

/** One scope label for a row: the globs it covers, or "every path" for a whole-tool rule. */
export function scopeLabel(row: RuleView): string {
  const globs = row.globs.filter(Boolean);
  if (!globs.length || globs.includes("*")) return "*";
  return globs.join(", ");
}
