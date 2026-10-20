import type { Locale } from "../../i18n";
import { planningCopy } from "../../i18n/planning";
import { waitingLabel } from "../../i18n/questions";
import { currentContext, taskFiles } from "../../lib/timeline";
import type { RunState } from "../../store/run";
import { PlanChecklist } from "./plan-checklist";

export function RunInfo({ run, locale, waiting }: { run: RunState; locale: Locale; waiting: number }) {
  const t = planningCopy(locale), number = new Intl.NumberFormat(locale);
  const context = currentContext(run.events), files = taskFiles(run.events);
  const children = run.events.filter(e => e.type === "subagent.started");
  return <aside className="run-info">
    {run.plan ? <PlanChecklist plan={run.plan} locale={locale} /> : <section><h2>{t.plan}</h2><p className="muted">{run.status === "running" ? t.noPlan : t.noPlanHistory}</p></section>}
    <section><h2>{t.delegates} ({number.format(children.length)})</h2>{children.map(child => {
      const end = run.events.slice().reverse().find(e => e.type === "subagent.finished" && e.scope.scope_id === child.scope.scope_id);
      return <p className="info-row" key={child.scope.scope_id}><span>{child.scope.agent === "reviewer" ? t.reviewer : t.researcher}</span><span className="muted">{end?.type === "subagent.finished" ? t[end.status] : t.running}</span></p>;
    })}</section>
    <section><h2>{t.context}</h2>{context?.type === "context.updated" && context.context_window ? <><p className="muted">{context.estimated ? "~" : ""}{number.format(context.input_tokens)} / {context.context_window_estimated ? "~" : ""}{number.format(context.context_window)}</p><progress aria-label={t.context} value={Math.min(context.input_tokens, context.context_window)} max={context.context_window} /></> : <p className="muted">{t.unavailable}</p>}</section>
    <section><h2>{t.limits}</h2><p className="info-row"><span>{t.steps}</span><span className="muted">{t.unavailable}</span></p><p className="info-row"><span>{t.fixes}</span><span className="muted">{t.unavailable}</span></p></section>
    {files.length > 0 && <section><h2>{t.files}</h2>{files.map(([path, state]) => <p className="info-file" key={path}><code dir="ltr">{path}</code><span className="muted">{state === "changed" ? t.writes : state === "pending" ? t.pending : t.read}</span></p>)}</section>}
    {waiting > 0 && <div className="current-waiting" role="status" data-testid="current-waiting">{waitingLabel(waiting, locale)}</div>}
  </aside>;
}
