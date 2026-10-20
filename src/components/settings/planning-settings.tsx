import type { Session } from "../../lib/use-session";
import { usePlanningSettings } from "../../lib/use-planning-settings";
import { planningCopy } from "../../i18n/planning";
import { ApprovalCard } from "../approvals/approval-card";

export function PlanningSettingsForm({ session }: { session: Session }) {
  const settings = usePlanningSettings(session.workspace), t = planningCopy(session.locale), value = settings.value;
  return <section className="model-card planning-settings"><h3>{t.settings}</h3>
    {value && <form onSubmit={event => { event.preventDefault(); void settings.save(); }}>
      <label>{t.stepThreshold}<input type="number" min={1} max={64} required value={value.step_threshold} onChange={event => settings.setValue({ ...value, step_threshold: event.target.valueAsNumber })} /></label>
      <label>{t.fileThreshold}<input type="number" min={1} max={10000} required value={value.file_threshold} onChange={event => settings.setValue({ ...value, file_threshold: event.target.valueAsNumber })} /></label>
      <label className="planning-toggle"><input type="checkbox" checked={value.deviation_gate} onChange={event => settings.setValue({ ...value, deviation_gate: event.target.checked })} />{t.deviation}</label>
      <p className="muted">{t.fixedRisk}</p><button className="light-button" disabled={settings.saving || settings.approval?.status === "pending"}>{t.save}</button>
    </form>}
    {settings.error && <p className="error" role="alert">{t.configError}</p>}
    {settings.approval && <><p role="status">{t.review}</p><ApprovalCard record={settings.approval} locale={session.locale} inline /></>}
  </section>;
}
