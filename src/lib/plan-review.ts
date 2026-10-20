import type { ApprovalRequest } from "./protocol";
import type { Locale } from "../i18n";

const reasons = {
  step_threshold: ["The plan reaches your step threshold.", "تعداد گام‌های برنامه به آستانه بازبینی رسیده است."],
  file_threshold: ["The plan exceeds your file threshold.", "تعداد فایل‌های برنامه از آستانه بازبینی بیشتر است."],
  uncertain_file_scope: ["The complete file scope cannot be counted safely.", "شمارش دقیق همه فایل‌های برنامه ممکن نیست."],
  high_risk: ["The plan contains a high-risk step.", "برنامه شامل یک گام پرخطر است."],
  dropped_step: ["A step would be dropped from the accepted plan.", "یک گام از برنامه پذیرفته‌شده حذف می‌شود."],
  added_steps: ["More than two steps would be added since the last review.", "بیش از دو گام از زمان آخرین بازبینی اضافه می‌شود."],
  changed_scope_or_risk: ["The accepted file scope, risk or verification command would change.", "محدوده فایل‌ها، خطر یا دستور بررسی برنامه تغییر می‌کند."],
};
export function planReviewReason(request: ApprovalRequest, locale: Locale): string | null {
  if (!request.reason?.startsWith("Plan review:")) return null;
  return request.reason.slice("Plan review:".length).trim().split(", ").map(reason => reasons[reason as keyof typeof reasons]?.[locale === "fa" ? 1 : 0] ?? reason).join(" ");
}
export function planReviewSteps(request: ApprovalRequest): { id: string; title: string; files: string[]; verify: string | null }[] {
  const steps = request.plan_proposed?.steps;
  if (!Array.isArray(steps)) return [];
  return steps.flatMap(step => {
    if (!step || typeof step !== "object" || Array.isArray(step) || typeof step.id !== "string" || typeof step.title !== "string") return [];
    return [{ id: step.id, title: step.title, files: Array.isArray(step.expected_files) ? step.expected_files.filter((file: unknown): file is string => typeof file === "string") : [], verify: typeof step.verify_command === "string" ? step.verify_command : null }];
  });
}
