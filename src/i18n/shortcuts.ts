import type { Locale } from ".";
/**
 * What each row of `src/lib/shortcuts.ts` does, in a sentence.
 *
 * The table names the key; this file says what it means. A test asserts every row has a
 * sentence in both locales, so a new shortcut cannot ship undocumented.
 */
const en = {
  send: "Send the task",
  newline: "Add a line instead of sending",
  command: "Open the command list",
  mention: "Open the file list",
  dismiss: "Close the list that is open",
  pick: "Pick an answer by its number",
  other: "Write your own answer",
  advance: "Move to the next question",
  decline: "Decline the questions",
  approve: "Approve the request",
  reject: "Reject the request",
  next: "Move to the next request",
  previous: "Move to the previous request",
  close: "Close the dialog",
};
const fa: typeof en = {
  send: "ارسال کار",
  newline: "خط تازه به‌جای ارسال",
  command: "باز کردن فهرست فرمان‌ها",
  mention: "باز کردن فهرست فایل‌ها",
  dismiss: "بستن فهرست باز",
  pick: "انتخاب پاسخ با شماره‌ی آن",
  other: "نوشتن پاسخ دلخواه",
  advance: "رفتن به پرسش بعدی",
  decline: "رد کردن پرسش‌ها",
  approve: "تأیید درخواست",
  reject: "رد درخواست",
  next: "رفتن به درخواست بعدی",
  previous: "رفتن به درخواست پیشین",
  close: "بستن پنجره",
};
export const shortcutsCopy = (locale: Locale) => locale === "fa" ? fa : en;
/** The scope names, so a help surface can label its groups. */
const scopes = {
  en: { composer: "Writing a task", questions: "Answering questions", approval: "Reviewing a request", inbox: "The approvals list", dialog: "Any dialog" },
  fa: { composer: "نوشتن کار", questions: "پاسخ به پرسش‌ها", approval: "بررسی درخواست", inbox: "فهرست تأییدها", dialog: "هر پنجره" },
};
export const scopeCopy = (locale: Locale) => locale === "fa" ? scopes.fa : scopes.en;
