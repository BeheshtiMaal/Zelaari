import type { Locale } from "../i18n";
const en = {
  plan: "Plan", analysis: "Analysis and history", approved: "Approved", automatic: "Automatically adopted",
  pending: "Pending", rejected: "Rejected", in_progress: "In progress", completed: "Completed", failed: "Failed",
  stopped: "Stopped", interrupted: "Interrupted", cancelled: "Cancelled", running: "Running",
  thinking: "Thinking", noReason: "Thinking: this model did not send reasoning", awaiting: "Waiting for the model",
  delegates: "Sub-agents", reviewer: "Reviewer", researcher: "Researcher", readOnly: "Read-only",
  summary: "Conversation context summarized", messages: "messages", context: "Context", unavailable: "Unavailable",
  limits: "Limits", steps: "Steps", fixes: "Fix attempts", files: "Task files", read: "Read", writes: "Writes",
  commands: "Commands", seconds: "s", queued: "Queued", delivered: "Delivered", steering: "Task guidance",
  sendError: "Message was not sent. Your draft is saved; try again.", save: "Review settings change",
  settings: "Planning", stepThreshold: "Review plans with at least this many steps",
  fileThreshold: "Review plans exceeding this many files", deviation: "Review changes outside the accepted plan",
  fixedRisk: "High-risk plans always require review outside Auto mode.", configError: "Could not load or propose planning settings.",
  review: "Review the settings change below.", noPlan: "The agent is analyzing the task.", noPlanHistory: "No submitted plan.",
};
const fa: typeof en = {
  plan: "برنامه", analysis: "تحلیل و سابقه", approved: "تأیید شده", automatic: "پذیرفته‌شده خودکار",
  pending: "در انتظار", rejected: "رد شده", in_progress: "در حال اجرا", completed: "تمام شد", failed: "ناموفق",
  stopped: "متوقف شد", interrupted: "قطع شد", cancelled: "لغو شد", running: "در حال اجرا",
  thinking: "تفکر", noReason: "تفکر: این مدل استدلال ارسال نکرد", awaiting: "در انتظار پاسخ مدل",
  delegates: "زیرعامل‌ها", reviewer: "بازبین", researcher: "پژوهشگر", readOnly: "فقط خواندنی",
  summary: "زمینه گفتگو خلاصه شد", messages: "پیام", context: "زمینه", unavailable: "در دسترس نیست",
  limits: "سقف‌ها", steps: "گام‌ها", fixes: "تلاش اصلاح", files: "فایل‌های کار", read: "خواندن", writes: "نوشتن",
  commands: "دستور", seconds: "ثانیه", queued: "در صف", delivered: "تحویل داده شد", steering: "راهنمایی کار",
  sendError: "پیام ارسال نشد. پیش‌نویس حفظ شده؛ دوباره تلاش کنید.", save: "بازبینی تغییر تنظیمات",
  settings: "برنامه‌ریزی", stepThreshold: "بازبینی برنامه از این تعداد گام",
  fileThreshold: "بازبینی برنامه با بیش از این تعداد فایل", deviation: "بازبینی خروج از برنامه پذیرفته‌شده",
  fixedRisk: "برنامه پرخطر خارج از حالت خودکار همیشه نیازمند تأیید است.", configError: "بارگذاری یا پیشنهاد تنظیمات ممکن نشد.",
  review: "تغییر تنظیمات را در پایین بازبینی کنید.", noPlan: "عامل در حال تحلیل کار است.", noPlanHistory: "برنامه‌ای ثبت نشده است.",
};
export const planningCopy = (locale: Locale) => locale === "fa" ? fa : en;
