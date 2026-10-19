import type { Locale } from ".";
const en = {
  question: "Question", of: "of", other: "Other…", send: "Send answer", next: "Next", back: "Back",
  decline: "Decline", choose: "to choose", enter: "Enter to send", pending: "Waiting for your answer",
  answered: "Answered", declined: "Declined", cancelled: "Cancelled", error: "Answer could not be sent. Check the fields and try again.",
  required: "Answer this question before continuing.", moveUp: "Move up", moveDown: "Move down",
  waiting: "items waiting for you", grill: "Interview with grill-me", command: "Interview to clarify the task before implementation",
  retry: "Retry with a hint", change: "Change approach", stop: "Stop and report", hint: "Write your guidance",
  recovery: "Attempts exhausted", order: "Order", options: "Options", dismissPicker: "Close commands",
};
const fa: typeof en = {
  question: "سؤال", of: "از", other: "گزینه‌ی دیگر…", send: "ارسال پاسخ", next: "بعدی", back: "قبلی",
  decline: "صرف‌نظر", choose: "برای انتخاب", enter: "Enter برای ارسال", pending: "منتظر پاسخ شما",
  answered: "پاسخ داده شد", declined: "صرف‌نظر شد", cancelled: "لغو شد", error: "ارسال پاسخ ناموفق بود. ورودی‌ها را بررسی کنید و دوباره تلاش کنید.",
  required: "پیش از ادامه به این سؤال پاسخ دهید.", moveUp: "بالاتر", moveDown: "پایین‌تر",
  waiting: "مورد منتظر شماست", grill: "مصاحبه با grill-me", command: "مصاحبه برای روشن شدن کار پیش از پیاده‌سازی",
  retry: "با یک راهنمایی دوباره تلاش کن", change: "رویکرد را عوض کن", stop: "متوقف شو و گزارش بده", hint: "راهنمایتان را بنویسید",
  recovery: "تلاش‌ها تمام شد", order: "ترتیب", options: "گزینه‌ها", dismissPicker: "بستن دستورها",
};
export const questionCopy = (locale: Locale) => locale === "fa" ? fa : en;
