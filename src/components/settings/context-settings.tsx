"use client";
import { useEffect, useState } from "react";
import { verifyCopy } from "../../i18n/verify-settings";
import type { Session } from "../../lib/use-session";
import { useVerifySettings } from "../../lib/use-verify-settings";
import {
  BOUNDS,
  compactionPercent,
  keepMessages,
  percentText,
  withContext,
  withVerify,
} from "../../lib/verify-settings";
import { NumberField, Row, SaveBar, Switch } from "./verify-rows";
import { ApprovalCard } from "../approvals/approval-card";

export function ContextSettingsForm({ session }: { session: Session }) {
  const t = verifyCopy(session.locale), settings = useVerifySettings(session.workspace);
  const [saved, setSaved] = useState(false);
  const value = settings.value;
  useEffect(() => { setSaved(false); }, [settings.approval?.status]);
  if (!value) return <div className="deferred-panel">{settings.error ? t.error : t.loading}</div>;
  const context = value.context, verify = value.verify;
  const percent = compactionPercent(context);
  const change = (next: typeof value) => { settings.setValue(next); setSaved(false); };
  return <div className="verify-settings" data-testid="context-settings">
    <section className="model-card">
      <h3>{t.window}</h3>
      <Row title={t.size} help={t.sizeHelp}>
        <span className="verify-badge" data-testid="context-window">{t.automatic}</span>
      </Row>
      <Row title={t.compactAt} help={t.compactHelp}>
        <div className="verify-range">
          <input type="range" min={BOUNDS.compaction.min} max={BOUNDS.compaction.max} step={BOUNDS.compaction.step}
            value={percent} aria-label={t.compactAt} data-testid="context-percent"
            onChange={event => change(withContext(value, { compaction_percent: Number(event.target.value) }))} />
          <span data-testid="context-percent-value">{percentText(percent, session.locale)}</span>
        </div>
      </Row>
      <Row title={t.keep} help={t.keepHelp}>
        <NumberField value={keepMessages(context)} min={BOUNDS.keep.min} max={BOUNDS.keep.max} locale={session.locale}
          label={t.keep} testId="context-keep"
          onChange={next => change(withContext(value, { keep_messages: next }))} />
      </Row>
      <Row title={t.offload} help={t.offloadHelp}>
        <Switch checked={context?.offload ?? true} label={t.offload} testId="context-offload"
          onChange={next => change(withContext(value, { offload: next }))} />
      </Row>
      <Row title={t.ring}>
        <Switch checked={context?.show_ring ?? true} label={t.ring} testId="context-ring-switch"
          onChange={next => change(withContext(value, { show_ring: next }))} />
      </Row>
    </section>
    <section className="model-card">
      <h3>{t.limits}</h3>
      <Row title={t.maxSteps}>
        <NumberField value={verify?.max_steps ?? BOUNDS.steps.fallback} min={BOUNDS.steps.min} max={BOUNDS.steps.max}
          locale={session.locale} label={t.maxSteps} testId="verify-steps"
          onChange={next => change(withVerify(value, { max_steps: next }))} />
      </Row>
      <Row title={t.maxMinutes}>
        <div className="verify-unit">
          <NumberField value={verify?.max_minutes ?? BOUNDS.minutes.fallback} min={BOUNDS.minutes.min}
            max={BOUNDS.minutes.max} locale={session.locale} label={t.maxMinutes} testId="verify-minutes"
            onChange={next => change(withVerify(value, { max_minutes: next }))} />
          <span className="muted">{t.minutes}</span>
        </div>
      </Row>
      <Row title={t.fixAttempts} help={t.fixHelp}>
        <NumberField value={verify?.fix_attempts ?? BOUNDS.fixes.fallback} min={BOUNDS.fixes.min} max={BOUNDS.fixes.max}
          locale={session.locale} label={t.fixAttempts} testId="verify-fixes"
          onChange={next => change(withVerify(value, { fix_attempts: next }))} />
      </Row>
    </section>
    <section className="model-card">
      <h3>{t.usage}</h3>
      <Row title={t.usageHelp}><span className="verify-badge">{t.tokens}</span></Row>
    </section>
    <SaveBar saving={settings.saving || settings.approval?.status === "pending"} error={settings.error} saved={saved}
      copy={t} onSave={() => { setSaved(true); void settings.save(); }} />
    {settings.approval && <><p role="status">{t.review}</p><ApprovalCard record={settings.approval} locale={session.locale} inline /></>}
  </div>;
}
