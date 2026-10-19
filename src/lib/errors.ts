/** Recognise the two engine failures that get their own card (R30, R31). */

export interface JailBlock {
  kind: "jail";
  path: string;
}

export interface CommandTimeout {
  kind: "timeout";
  command: string;
  seconds: number;
}

export type ToolFailure = JailBlock | CommandTimeout | null;

/** Must match `tools/jail.py:jail_message` exactly; the engine owns this sentence. */
const BLOCK_PREFIX = "Access blocked: ";
const BLOCK_SUFFIX = " is outside the workspace. Access is never allowed, even with approval.";

export function jailBlock(text: string): JailBlock | null {
  const start = text.indexOf(BLOCK_PREFIX);
  if (start < 0) return null;
  const rest = text.slice(start + BLOCK_PREFIX.length);
  const end = rest.indexOf(BLOCK_SUFFIX);
  if (end < 0) return null;
  return { kind: "jail", path: rest.slice(0, end) };
}

export function commandTimeout(text: string): CommandTimeout | null {
  try {
    const value = JSON.parse(text) as { command?: unknown; timed_out?: unknown; timeout_seconds?: unknown };
    if (value.timed_out !== true) return null;
    return {
      kind: "timeout",
      command: typeof value.command === "string" ? value.command : "",
      seconds: typeof value.timeout_seconds === "number" ? value.timeout_seconds : 120,
    };
  } catch {
    return null;
  }
}

export function toolFailure(text: string): ToolFailure {
  return commandTimeout(text) ?? jailBlock(text);
}

/** `{seconds}` interpolation for the two cards, in the active locale's digits. */
export function fill(template: string, values: Record<string, string | number>, locale: string): string {
  return template.replace(/\{(\w+)\}/g, (whole, key: string) =>
    key in values ? new Intl.NumberFormat(locale).format(Number(values[key])) : whole);
}
