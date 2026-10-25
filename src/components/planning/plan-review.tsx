import type { ApprovalRequest } from "../../lib/protocol";
import type { Locale } from "../../i18n";
import { planReviewReason, planReviewSteps } from "../../lib/plan-review";
import { planningCopy } from "../../i18n/planning";

export function PlanReview({ request, locale }: { request: ApprovalRequest; locale: Locale }) {
  const steps = planReviewSteps(request), reason = planReviewReason(request, locale), t = planningCopy(locale);
  const known = request.plan_file_scope?.known_files;
  return <section className="plan-review" aria-label={t.plan}>
    {reason && <p>{reason}</p>}
    {Array.isArray(known) && <p className="muted">{new Intl.NumberFormat(locale).format(known.length)} {t.files}{request.plan_file_scope?.uncertain ? ` · ${t.scopeUncertain}` : ""}</p>}
    <ol>{steps.map(step => <li key={step.id}><strong>{step.title}</strong>{step.files.map(path => <code dir="ltr" key={path}>{path}</code>)}{step.verify && <pre className="command-preview" dir="ltr">{step.verify}</pre>}</li>)}</ol>
  </section>;
}
