import type { ScheduleCopy } from "../i18n/schedule";
import type { Locale } from "../i18n";
import { localeDigits } from "./localised-number";
import type { ScheduleInput, ScheduleRecord } from "./protocol";

export type ScheduleMode = "read-only" | "ask" | "auto";
export type ScheduleCeiling = "report" | "full";
export type ScheduleRepeat = "daily" | "weekly";
export type ScheduleStatus = "running" | "completed" | "error" | "stopped" | "interrupted" | "missed";

/**
 * A schedule as the screen uses it: every optional wire field resolved to the engine's own
 * default, and camelCase throughout. One conversion, one place that knows the defaults.
 */
export interface Schedule {
  id: string;
  name: string;
  prompt: string;
  workspace: string;
  model: string;
  mode: ScheduleMode;
  ceiling: ScheduleCeiling;
  repeat: ScheduleRepeat;
  weekday: number | null;
  time: string;
  validUntil: string | null;
  enabled: boolean;
  createdAt: string;
  nextRunAt: string | null;
  lastRunAt: string | null;
  lastStatus: ScheduleStatus | null;
  lastRunId: string | null;
  missedAt: string | null;
  lastError: string | null;
}

const MODES: ScheduleMode[] = ["read-only", "ask", "auto"];
const STRICTNESS: Record<string, number> = { "read-only": 0, ask: 1, auto: 2, report: 0, full: 2 };

/**
 * The stricter of the two. The engine computes this again when the run starts and its answer
 * is the one that counts; this exists so the dialog can say what will happen before a round
 * trip. Both sides carry the same six-cell table in a test (D42).
 */
export function effectiveMode(mode: ScheduleMode, ceiling: ScheduleCeiling): ScheduleMode {
  return MODES[Math.min(STRICTNESS[mode], STRICTNESS[ceiling])];
}

function mode(value: string | undefined): ScheduleMode {
  return value === "ask" || value === "auto" ? value : "read-only";
}

function status(value: string | null | undefined): ScheduleStatus | null {
  return value === "running" ||
    value === "completed" ||
    value === "error" ||
    value === "stopped" ||
    value === "interrupted" ||
    value === "missed"
    ? value
    : null;
}

export function toSchedule(record: ScheduleRecord): Schedule {
  return {
    id: record.id,
    name: record.name,
    prompt: record.prompt,
    workspace: record.workspace,
    model: record.model,
    mode: mode(record.mode),
    ceiling: record.ceiling === "full" ? "full" : "report",
    repeat: record.repeat === "weekly" ? "weekly" : "daily",
    weekday: typeof record.weekday === "number" ? record.weekday : null,
    time: record.time ?? "02:00",
    validUntil: record.valid_until ?? null,
    enabled: record.enabled ?? true,
    createdAt: record.created_at,
    nextRunAt: record.next_run_at ?? null,
    lastRunAt: record.last_run_at ?? null,
    lastStatus: status(record.last_status),
    lastRunId: record.last_run_id ?? null,
    missedAt: record.missed_at ?? null,
    lastError: record.last_error ?? null,
  };
}

/** `HH:MM` in the reader's digits. A clock time is text, not code, so it stays in the flow. */
export function formatTime(value: string, locale: Locale): string {
  return localeDigits(value, locale);
}

function dayOf(iso: string): string {
  return iso.slice(0, 10);
}

function shiftDay(day: string, days: number): string {
  const [year, month, date] = day.split("-").map(Number);
  // UTC arithmetic so a daylight-saving boundary cannot turn "yesterday" into "two days ago".
  const stamp = Date.UTC(year, month - 1, date) + days * 86_400_000;
  return new Date(stamp).toISOString().slice(0, 10);
}

function calendarDay(day: string, locale: Locale): string {
  const [year, month, date] = day.split("-").map(Number);
  return new Intl.DateTimeFormat(locale === "fa" ? "fa-IR" : "en-GB", {
    day: "numeric",
    month: "short",
  }).format(new Date(Date.UTC(year, month - 1, date)));
}

/** Today / tomorrow / yesterday by name, anything else as a date. Compares calendar days only. */
export function dayLabel(iso: string, now: string, locale: Locale, copy: ScheduleCopy): string {
  const day = dayOf(iso);
  const today = dayOf(now);
  if (day === today) return copy.today;
  if (day === shiftDay(today, 1)) return copy.tomorrow;
  if (day === shiftDay(today, -1)) return copy.yesterday;
  return calendarDay(day, locale);
}

/** "Every night at 02:00" or "Fridays at 09:00", the way the mock writes it. */
export function recurrenceLabel(schedule: Schedule, copy: ScheduleCopy, locale: Locale): string {
  const time = formatTime(schedule.time, locale);
  if (schedule.repeat === "weekly" && schedule.weekday !== null) {
    return `${copy.weekdays[schedule.weekday] ?? copy.weekdays[0]} ${copy.at} ${time}`;
  }
  return `${copy.repeats[schedule.repeat]} ${copy.at} ${time}`;
}

export function isExpired(schedule: Schedule): boolean {
  return schedule.nextRunAt === null;
}

/** A missed occurrence still waiting for a decision. */
export function isMissed(schedule: Schedule): boolean {
  return schedule.missedAt !== null;
}

export function nextRunLabel(
  schedule: Schedule,
  now: string,
  copy: ScheduleCopy,
  locale: Locale,
): string {
  if (isExpired(schedule)) return copy.expired;
  if (schedule.nextRunAt === null) return copy.never;
  return `${copy.nextRun}: ${dayLabel(schedule.nextRunAt, now, locale, copy)} · ${formatTime(schedule.time, locale)}`;
}

function statusLabel(value: ScheduleStatus, copy: ScheduleCopy): string {
  return copy[value];
}

/**
 * What the row says after the mode chip: a queued approval outranks a result, because a
 * person waiting is the thing that needs attention.
 */
export function lastResultLabel(
  schedule: Schedule,
  pending: number,
  now: string,
  copy: ScheduleCopy,
  locale: Locale,
): { text: string; tone: "ok" | "warn" | "danger" | "muted" } {
  if (pending > 0) {
    return {
      text: pending === 1 ? copy.queuedOne : copy.queued.replace("{count}", localeDigits(pending, locale)),
      tone: "warn",
    };
  }
  if (isMissed(schedule)) return { text: copy.missed, tone: "warn" };
  if (schedule.lastError !== null) return { text: copy.error, tone: "danger" };
  if (schedule.lastStatus === null || schedule.lastRunAt === null) {
    return { text: copy.never, tone: "muted" };
  }
  const day = dayLabel(schedule.lastRunAt, now, locale, copy);
  const tone = schedule.lastStatus === "completed" ? "ok" : schedule.lastStatus === "running" ? "muted" : "danger";
  return { text: `${copy.lastRun}: ${day} · ${statusLabel(schedule.lastStatus, copy)}`, tone };
}

/** The prefill for "edit": exactly what the dialog needs to send back. */
export function inputFrom(schedule: Schedule): ScheduleInput {
  return {
    name: schedule.name,
    prompt: schedule.prompt,
    workspace: schedule.workspace,
    model: schedule.model,
    mode: schedule.mode,
    ceiling: schedule.ceiling,
    repeat: schedule.repeat,
    weekday: schedule.weekday,
    time: schedule.time,
    valid_until: schedule.validUntil,
    enabled: schedule.enabled,
  };
}
