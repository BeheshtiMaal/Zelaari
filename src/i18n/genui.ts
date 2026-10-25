import type { Locale } from ".";
const en = {
  notFound: "Not found in this run",
  notFoundHelp: "This id does not belong to the run that is open.",
  changedFiles: "Files this run changed",
  noChangedFiles: "This run has not changed a file yet.",
  files: "{count} files",
  loadingFiles: "Reading the changed files…",
  tabList: "Sections",
  table: "Table",
};
const fa: typeof en = {
  notFound: "در این اجرا پیدا نشد",
  notFoundHelp: "این شناسه به اجرایی که باز است تعلق ندارد.",
  changedFiles: "فایل‌هایی که این اجرا تغییر داده",
  noChangedFiles: "این اجرا هنوز فایلی را تغییر نداده است.",
  files: "{count} فایل",
  loadingFiles: "خواندن فایل‌های تغییر‌یافته…",
  tabList: "بخش‌ها",
  table: "جدول",
};
export const genuiCopy = (locale: Locale) => locale === "fa" ? fa : en;
export function fileCount(text: string, count: number, locale: Locale) {
  return text.replace("{count}", new Intl.NumberFormat(locale).format(count));
}
