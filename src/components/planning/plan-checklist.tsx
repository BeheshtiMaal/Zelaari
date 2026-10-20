"use client";
import type { Locale } from "../../i18n";
import { planningCopy } from "../../i18n/planning";
import type { PlanRecord } from "../../lib/protocol";
import { trustedPlan } from "../../lib/timeline";
import { useRun } from "../../store/run";
import { dictionary } from "../../i18n";

export function PlanChecklist({ plan, locale }: { plan: PlanRecord; locale: Locale }) {
  const t = planningCopy(locale), number = new Intl.NumberFormat(locale);
  const completed = plan.progress.filter(item => item.status === "completed").length;
  return <section className="plan-checklist" data-testid="plan-checklist" aria-label={t.plan}>
    <div className="plan-heading"><strong>{t.plan}</strong><span className={`adoption ${plan.adoption}`}>{t[plan.adoption]}</span></div>
    <progress value={completed} max={plan.submission.steps.length} aria-label={t.plan} />
    <span className="muted">{number.format(completed)} {locale === "fa" ? "از" : "/"} {number.format(plan.submission.steps.length)}</span>
    <ol>{plan.submission.steps.map((step, index) => <li key={step.id} data-status={plan.progress[index]?.status}>
      <span className="step-mark" aria-hidden="true">{plan.progress[index]?.status === "completed" ? "✓" : number.format(index + 1)}</span>
      <span>{step.title}<small>{t[plan.progress[index]?.status ?? "pending"]}</small></span>
    </li>)}</ol>
  </section>;
}
export function RegisteredPlanChecklist(props: { runId: string; planId: string; revision: string }) {
  const run = useRun(), locale = typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "fa";
  const plan = trustedPlan(run.plan, run.runId, props);
  return plan ? <PlanChecklist plan={plan} locale={locale} /> : <p className="muted">{dictionary(locale).error}</p>;
}
