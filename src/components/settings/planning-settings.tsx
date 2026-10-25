import type { Session } from "../../lib/use-session";
import { usePlanningSettings } from "../../lib/use-planning-settings";
import { planningCopy } from "../../i18n/planning";
import { ApprovalCard } from "../approvals/approval-card";
import { NumberField, Row, Switch } from "./verify-rows";

/** The bounds the contract enforces, so the field cannot ask for a value the engine refuses. */
const STEPS = { min: 1, max: 64, fallback: 4 } as const;
const FILES = { min: 1, max: 10000, fallback: 3 } as const;

/** The plan gate and its thresholds. A save is a protected change, so it lands in the inbox. */
export function PlanningSettingsForm({ session }: { session: Session }) {
  const settings = usePlanningSettings(session.workspace), t = planningCopy(session.locale), value = settings.value;
  return <section className="model-card planning-settings" data-testid="plan-approval">
    <h3>{t.settings}</h3>
    {value && <form onSubmit={event => { event.preventDefault(); void settings.save(); }}>
      <Row title={t.planGate} help={t.planGateHelp}>
        <Switch checked={value.plan_gate ?? true} label={t.planGate} testId="plan-gate"
          onChange={next => settings.setValue({ ...value, plan_gate: next })} />
      </Row>
      <Row title={t.stepThreshold} help={t.stepHelp}>
        <NumberField value={value.step_threshold ?? STEPS.fallback} min={STEPS.min}
          max={STEPS.max} locale={session.locale} label={t.stepThreshold} testId="plan-steps"
          onChange={next => settings.setValue({ ...value, step_threshold: next })} />
      </Row>
      <Row title={t.fileThreshold} help={t.fileHelp}>
        <NumberField value={value.file_threshold ?? FILES.fallback} min={FILES.min}
          max={FILES.max} locale={session.locale} label={t.fileThreshold} testId="plan-files"
          onChange={next => settings.setValue({ ...value, file_threshold: next })} />
      </Row>
      <Row title={t.deviation}>
        <Switch checked={value.deviation_gate ?? true} label={t.deviation} testId="plan-deviation"
          onChange={next => settings.setValue({ ...value, deviation_gate: next })} />
      </Row>
      <p className="muted">{t.fixedRisk}</p>
      <div className="verify-save">
        <button className="light-button" data-testid="plan-save" disabled={settings.saving || settings.approval?.status === "pending"}>{t.save}</button>
        {settings.error && <p className="error" role="alert">{t.configError}</p>}
      </div>
    </form>}
    {settings.approval && <><p role="status">{t.review}</p><ApprovalCard record={settings.approval} locale={session.locale} inline /></>}
  </section>;
}
