import type { Locale } from ".";
const en = {
  noWorkspace: {
    label: "First use · no workspace selected",
    title: "No project folder yet",
    help: "Choose the folder the agent may work in. It reads and writes nothing outside it.",
    primary: "Choose folder",
    sample: "Sample project",
  },
  noModel: {
    label: "First use · no model added",
    title: "No model added yet",
    help: "Add a model with your own key, or start with the offline demo — no key, no internet.",
    primary: "Add model",
    demo: "Use the demo model",
  },
  emptyInbox: {
    label: "Nothing waiting",
    title: "No approvals to review",
    help: "When the agent needs a decision it stops and waits here. Right now it is not waiting for anything.",
    primary: "Back to the task",
  },
  noSchedules: {
    label: "Nothing scheduled",
    title: "No schedules yet",
    help: "A schedule runs a task at a set time. This build has no scheduler, so nothing can be added here.",
    primary: "Back to the task",
  },
  noTasks: {
    label: "No runs yet",
    title: "This project has no runs",
    help: "Runs you start in this project appear here, with their events, so you can reopen them later.",
    primary: "Start a task",
  },
  noSkills: {
    label: "Nothing enabled",
    title: "No skill is switched on",
    help: "A skill is a capability the agent loads when it needs it. Switch on the ones this project should have.",
    primary: "Browse skills",
  },
  crash: {
    title: "The engine stopped unexpectedly",
    safe: "Your work is saved and nothing was left half-done. Restart the engine to keep working; the task you had open will be reopened from its saved events.",
    restart: "Restart the engine",
    restarting: "Restarting…",
    failed: "The engine did not come back. Open the log to see why, then restart again.",
    logs: "View the log",
    notice: "Engine stopped",
  },
};
const fa: typeof en = {
  noWorkspace: {
    label: "بار اول · فضای کاری انتخاب نشده",
    title: "هنوز پوشه‌ی پروژه‌ای انتخاب نکرده‌اید",
    help: "پوشه‌ای را انتخاب کنید که عامل اجازه‌ی کار در آن را دارد. بیرون از آن هیچ فایلی خوانده یا نوشته نمی‌شود.",
    primary: "انتخاب پوشه",
    sample: "پروژه‌ی نمونه",
  },
  noModel: {
    label: "بار اول · مدلی اضافه نشده",
    title: "هنوز مدلی اضافه نشده",
    help: "کلید API یک مدل را اضافه کنید، یا با مدل نمایشی بدون کلید و اینترنت شروع کنید.",
    primary: "افزودن مدل",
    demo: "مدل نمایشی",
  },
  emptyInbox: {
    label: "چیزی در انتظار نیست",
    title: "تأییدی برای بررسی نمانده",
    help: "وقتی عامل به تصمیم شما نیاز داشته باشد، اینجا می‌ایستد و منتظر می‌ماند. همین حالا منتظر چیزی نیست.",
    primary: "بازگشت به کار",
  },
  noSchedules: {
    label: "چیزی زمان‌بندی نشده",
    title: "هنوز زمان‌بندی‌ای نیست",
    help: "زمان‌بندی یک کار را در ساعتی مشخص اجرا می‌کند. این ساخت زمان‌بند ندارد، پس چیزی هم نمی‌شود اضافه کرد.",
    primary: "بازگشت به کار",
  },
  noTasks: {
    label: "هنوز اجرایی نیست",
    title: "این پروژه اجرایی ندارد",
    help: "اجراهایی که در این پروژه شروع می‌کنید با رویدادهایشان اینجا می‌مانند تا بعداً بازشان کنید.",
    primary: "شروع یک کار",
  },
  noSkills: {
    label: "هیچ‌کدام روشن نیست",
    title: "هیچ مهارتی روشن نیست",
    help: "مهارت توانایی‌ای است که عامل هنگام نیاز بار می‌کند. آن‌هایی را که این پروژه باید داشته باشد روشن کنید.",
    primary: "دیدن مهارت‌ها",
  },
  crash: {
    title: "موتور عامل ناگهان بسته شد",
    safe: "کار شما ذخیره شده و هیچ چیز نیمه‌کاره رها نشده است. برای ادامه موتور را دوباره راه بیندازید؛ کاری که باز بود از رویدادهای ذخیره‌شده باز می‌شود.",
    restart: "راه‌اندازی دوباره",
    restarting: "در حال راه‌اندازی…",
    failed: "موتور برنگشت. لاگ را ببینید و دوباره تلاش کنید.",
    logs: "مشاهده‌ی لاگ",
    notice: "موتور ایستاد",
  },
};
export const statesCopy = (locale: Locale) => locale === "fa" ? fa : en;
