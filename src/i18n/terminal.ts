import type { Locale } from ".";
const en = {
  exit: "exit code",
  showMore: "Show more",
  hidden: "lines hidden",
  running: "Running",
  timeout: "Command stopped after {seconds} seconds",
  timeoutTag: "Out of time",
  silent: "(no output for {seconds} seconds)",
  killed: "The agent ran the command but got no answer; the process and its children were killed.",
  passed: "passed",
  failed: "failed",
  noCounts: "Counts unknown",
  failures: "Failing tests",
  testResult: "Test result",
  timedOut: "Timed out",
  errored: "Could not run",
  terminal: "Terminal",
};
const fa: typeof en = {
  exit: "کد خروج",
  showMore: "نمایش بیشتر",
  hidden: "خط پنهان",
  running: "در حال اجرا",
  timeout: "دستور بعد از {seconds} ثانیه متوقف شد",
  timeoutTag: "پایان زمان",
  silent: "(بدون خروجی برای {seconds} ثانیه)",
  killed: "عامل دستور را اجرا کرد اما پاسخی نیامد؛ پردازش و زیرپردازش‌هایش بسته شدند.",
  passed: "موفق",
  failed: "ناموفق",
  noCounts: "تعداد نامشخص",
  failures: "آزمون‌های ناموفق",
  testResult: "نتیجه‌ی آزمون",
  timedOut: "مهلت تمام شد",
  errored: "اجرا نشد",
  terminal: "ترمینال",
};
export const terminalCopy = (locale: Locale) => locale === "fa" ? fa : en;
export function fill(text: string, seconds: number, locale: Locale) {
  return text.replace("{seconds}", new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(seconds));
}
