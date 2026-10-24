import type { Locale } from "../i18n";
import { bounded } from "./localised-number";
import type {
  ContextSettings,
  Detection,
  TerminalSettings,
  VerifySettings,
  VerifySettingsResponse,
} from "./protocol";

/** Every bound is the backend's bound; the field cannot hold a value a save would reject. */
export const BOUNDS = {
  compaction: { min: 30, max: 90, step: 5, fallback: 60 },
  keep: { min: 0, max: 50, fallback: 8 },
  steps: { min: 1, max: 200, fallback: 40 },
  minutes: { min: 1, max: 240, fallback: 30 },
  fixes: { min: 0, max: 10, fallback: 3 },
  timeout: { min: 1, max: 600, fallback: 120 },
  lines: { min: 20, max: 2000, fallback: 200 },
} as const;

export type TestMode = "auto" | "custom";
export const SHELLS = ["auto", "powershell", "cmd"] as const;
export type Shell = (typeof SHELLS)[number];

/** One section changes; the rest of the document is carried through untouched. */
export function withContext(value: VerifySettingsResponse, patch: Partial<ContextSettings>): VerifySettingsResponse {
  return { ...value, context: { ...value.context, ...patch } };
}

export function withVerify(value: VerifySettingsResponse, patch: Partial<VerifySettings>): VerifySettingsResponse {
  return { ...value, verify: { ...value.verify, ...patch } };
}

export function withTerminal(value: VerifySettingsResponse, patch: Partial<TerminalSettings>): VerifySettingsResponse {
  return { ...value, terminal: { ...value.terminal, ...patch } };
}

/** A blank command is "automatic", exactly like the backend reads it. */
export function testModeOf(verify: VerifySettings | undefined): TestMode {
  return verify?.command?.trim() ? "custom" : "auto";
}

/**
 * What a save would run for the chosen mode. `auto` clears the command so detection wins;
 * `custom` keeps what was typed, or starts from the detected command.
 */
export function commandFor(
  mode: TestMode,
  verify: VerifySettings | undefined,
  detection: Detection | undefined,
): string | null {
  if (mode === "auto") return null;
  const current = verify?.command?.trim();
  return current ? (verify?.command ?? null) : (detection?.command ?? "");
}

export interface DetectionLabel {
  /** The command that will run, or null when nothing was detected. */
  command: string | null;
  /** `از pyproject.toml` — only a file the detection actually read is named. */
  evidence: string | null;
  /** The "nothing detected" line, shown instead of a command. */
  empty: string | null;
}

export function detectionLabel(
  detection: Detection | undefined,
  copy: { detectedFrom: string; nothingDetected: string },
): DetectionLabel {
  const command = detection?.command ?? null;
  if (!command) return { command: null, evidence: null, empty: copy.nothingDetected };
  const source = detection?.source ?? "none";
  // `custom` is the box below, not evidence from a file.
  const evidence = source === "none" || source === "custom" ? null : `${copy.detectedFrom} ${source}`;
  return { command, evidence, empty: null };
}

export function shellOf(terminal: TerminalSettings | undefined): Shell {
  const value = terminal?.shell;
  return SHELLS.includes(value as Shell) ? (value as Shell) : "auto";
}

export function shellOptions(copy: { shellAuto: string }): { value: Shell; label: string }[] {
  return SHELLS.map(value => ({
    value,
    label: value === "auto" ? copy.shellAuto : value === "cmd" ? "CMD" : "PowerShell",
  }));
}

export function compactionPercent(value: ContextSettings | undefined): number {
  const raw = value?.compaction_percent;
  return bounded(typeof raw === "number" ? raw : null, BOUNDS.compaction.min, BOUNDS.compaction.max, BOUNDS.compaction.fallback);
}

export function keepMessages(value: ContextSettings | undefined): number {
  const raw = value?.keep_messages;
  return bounded(typeof raw === "number" ? raw : null, BOUNDS.keep.min, BOUNDS.keep.max, BOUNDS.keep.fallback);
}

/** `۶۰٪` — the slider's readout, in the reader's digits. */
export function percentText(percent: number, locale: Locale): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(percent)}٪`;
}
