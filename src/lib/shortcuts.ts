/**
 * The keyboard contract, in one table.
 *
 * Every handler in the app asks this module what a key means, so the table below is not a
 * description of the shortcuts: it is the implementation. A test walks `SHORTCUTS` and
 * checks the copy exists in both locales, which is why a row cannot be added without a
 * sentence to go with it.
 *
 * Two rules keep the table honest:
 * - Text wins. While the person is typing, `Enter` is a newline, not an approval.
 * - The first matching row wins, so a more specific key must sit above a general one.
 */

/** Where the key was pressed. A scope only answers for its own rows. */
export type Scope = "composer" | "questions" | "approval" | "inbox" | "dialog";

export type Action =
  | "send" | "newline" | "command" | "mention" | "dismiss"
  | "pick" | "other" | "advance" | "decline"
  | "approve" | "reject" | "next" | "previous" | "close";

/** The copy key in `src/i18n/shortcuts.ts` that describes this row to a person. */
export type CopyKey =
  | "send" | "newline" | "command" | "mention" | "dismiss"
  | "pick" | "other" | "advance" | "decline"
  | "approve" | "reject" | "next" | "previous" | "close";

/** The parts of a keyboard event the table reads, so a test can pass a plain object. */
export interface KeyLike {
  key: string;
  code?: string;
  shiftKey?: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  /** `event.target.tagName`, uppercased by the DOM. */
  tag?: string;
  contentEditable?: boolean;
}

export interface KeyContext {
  /** How many options the current question offers; the extra number focuses the free text. */
  optionCount?: number;
}

export interface Resolved {
  action: Action;
  /** For `pick`, the zero-based option. */
  index?: number;
}

interface Row {
  scope: Scope;
  /** How the key is written to a person. Tests assert this is non-empty and unique per scope. */
  keys: string;
  action: Action;
  copy: CopyKey;
  match(event: KeyLike, context: KeyContext): Resolved | null;
}

const PLAIN = (event: KeyLike) => !event.ctrlKey && !event.metaKey && !event.altKey;

/** A field that owns the key: typing in it must never trigger a shortcut. */
export function isTyping(event: KeyLike): boolean {
  return !!event.contentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(event.tag ?? "");
}

/**
 * The digit a key stands for, 1–4, or `NaN`.
 *
 * `code` is checked first because it names the physical key: on a Persian layout the
 * character is `۱` while the code is still `Digit1`.
 */
export function shortcutDigit(event: KeyLike): number {
  const code = event.code ?? "";
  if (/^Digit[1-4]$/.test(code) || /^Numpad[1-4]$/.test(code)) return Number(code.slice(-1));
  const persian = "۱۲۳۴".indexOf(event.key);
  if (persian >= 0) return persian + 1;
  return /^[1-4]$/.test(event.key) ? Number(event.key) : Number.NaN;
}

const key = (...names: string[]) => (event: KeyLike) => names.includes(event.key);

export const SHORTCUTS: readonly Row[] = [
  // Composer: a textarea that sends on Enter and grows on Shift+Enter.
  { scope: "composer", keys: "Shift+Enter", action: "newline", copy: "newline",
    match: event => PLAIN(event) && event.shiftKey && event.key === "Enter" ? { action: "newline" } : null },
  { scope: "composer", keys: "Enter", action: "send", copy: "send",
    match: event => PLAIN(event) && !event.shiftKey && event.key === "Enter" ? { action: "send" } : null },
  { scope: "composer", keys: "/", action: "command", copy: "command",
    match: event => PLAIN(event) && event.key === "/" ? { action: "command" } : null },
  { scope: "composer", keys: "@", action: "mention", copy: "mention",
    match: event => PLAIN(event) && event.key === "@" ? { action: "mention" } : null },
  { scope: "composer", keys: "Escape", action: "dismiss", copy: "dismiss",
    match: event => event.key === "Escape" ? { action: "dismiss" } : null },

  // Questions: numbers pick, the next number reaches the free-text answer.
  { scope: "questions", keys: "1–4", action: "pick", copy: "pick",
    match: (event, context) => {
      if (!PLAIN(event) || isTyping(event)) return null;
      const digit = shortcutDigit(event);
      const count = context.optionCount ?? 0;
      return digit >= 1 && digit <= count ? { action: "pick", index: digit - 1 } : null;
    } },
  { scope: "questions", keys: "1–4", action: "other", copy: "other",
    match: (event, context) => {
      if (!PLAIN(event) || isTyping(event)) return null;
      const digit = shortcutDigit(event);
      const count = context.optionCount ?? 0;
      return count > 0 && digit === count + 1 && digit <= 4 ? { action: "other" } : null;
    } },
  { scope: "questions", keys: "Enter", action: "advance", copy: "advance",
    match: event => {
      if (!PLAIN(event) || isTyping(event) || event.tag === "BUTTON") return null;
      return event.key === "Enter" ? { action: "advance" } : null;
    } },
  { scope: "questions", keys: "Escape", action: "decline", copy: "decline",
    match: event => !isTyping(event) && event.key === "Escape" ? { action: "decline" } : null },

  // Approvals: the decision is a keystroke, unless the focus is in a field or on a button.
  { scope: "approval", keys: "Enter", action: "approve", copy: "approve",
    match: event => {
      if (!PLAIN(event) || isTyping(event) || event.tag === "BUTTON") return null;
      return event.key === "Enter" ? { action: "approve" } : null;
    } },
  { scope: "approval", keys: "Escape", action: "reject", copy: "reject",
    match: event => !isTyping(event) && event.key === "Escape" ? { action: "reject" } : null },

  // The inbox list: arrows move the selection.
  { scope: "inbox", keys: "ArrowDown", action: "next", copy: "next",
    match: event => PLAIN(event) && !isTyping(event) && key("ArrowDown", "j")(event) ? { action: "next" } : null },
  { scope: "inbox", keys: "ArrowUp", action: "previous", copy: "previous",
    match: event => PLAIN(event) && !isTyping(event) && key("ArrowUp", "k")(event) ? { action: "previous" } : null },

  // Any dialog: Escape closes it. Radix also handles this, but a dialog of our own needs it.
  { scope: "dialog", keys: "Escape", action: "close", copy: "close",
    match: event => event.key === "Escape" ? { action: "close" } : null },
];

/** What this key means here, or `null` when the table has nothing to say about it. */
export function resolve(scope: Scope, event: KeyLike, context: KeyContext = {}): Resolved | null {
  for (const row of SHORTCUTS) {
    if (row.scope !== scope) continue;
    const hit = row.match(event, context);
    if (hit) return hit;
  }
  return null;
}

/** Every row in one scope, for a help surface or a test. */
export function rowsFor(scope: Scope): readonly Row[] {
  return SHORTCUTS.filter(row => row.scope === scope);
}

/** The scopes, in the order a person meets them. */
export const SCOPES: readonly Scope[] = ["composer", "questions", "approval", "inbox", "dialog"];
