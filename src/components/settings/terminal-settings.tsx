"use client";
import { useEffect, useState } from "react";
import { verifyCopy } from "../../i18n/verify-settings";
import type { Session } from "../../lib/use-session";
import { useVerifySettings } from "../../lib/use-verify-settings";
import {
  BOUNDS,
  commandFor,
  detectionLabel,
  shellOf,
  shellOptions,
  testModeOf,
  withTerminal,
  withVerify,
  type TestMode,
} from "../../lib/verify-settings";
import { NumberField, Row, SaveBar, Switch } from "./verify-rows";
import { ApprovalCard } from "../approvals/approval-card";

export function TerminalSettingsForm({ session }: { session: Session }) {
  const t = verifyCopy(session.locale), settings = useVerifySettings(session.workspace);
  const [saved, setSaved] = useState(false), [choice, setChoice] = useState<TestMode | null>(null);
  const value = settings.value;
  // A finished approval reloads the values, so the segment returns to what was stored.
  useEffect(() => { setSaved(false); setChoice(null); }, [settings.approval?.status]);
  if (!value) return <div className="deferred-panel">{settings.error ? t.error : t.loading}</div>;
  const terminal = value.terminal, verify = value.verify;
  const mode = choice ?? testModeOf(verify);
  const label = detectionLabel(value.detection, t);
  const change = (next: typeof value) => { settings.setValue(next); setSaved(false); };
  const choose = (next: TestMode) => {
    setChoice(next);
    change(withVerify(value, { command: commandFor(next, verify, value.detection) }));
  };
  return <div className="verify-settings" data-testid="terminal-settings">
    <section className="model-card">
      <h3>{t.terminal}</h3>
      <Row title={t.shell}>
        <select className="verify-select" data-testid="terminal-shell" aria-label={t.shell} value={shellOf(terminal)}
          onChange={event => change(withTerminal(value, { shell: event.target.value }))}>
          {shellOptions(t).map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </Row>
      <Row title={t.timeout} help={t.seconds}>
        <NumberField value={terminal?.timeout_seconds ?? BOUNDS.timeout.fallback} min={BOUNDS.timeout.min}
          max={BOUNDS.timeout.max} locale={session.locale} label={t.timeout} testId="terminal-timeout"
          onChange={next => change(withTerminal(value, { timeout_seconds: next }))} />
      </Row>
      <Row title={t.maxLines} help={t.maxLinesHelp}>
        <NumberField value={terminal?.max_output_lines ?? BOUNDS.lines.fallback} min={BOUNDS.lines.min}
          max={BOUNDS.lines.max} locale={session.locale} label={t.maxLines} testId="terminal-lines"
          onChange={next => change(withTerminal(value, { max_output_lines: next }))} />
      </Row>
      <Row title={t.env} help={t.envHelp}>
        <span className="verify-badge" data-testid="terminal-env">{t.envLocked}</span>
      </Row>
    </section>
    <section className="model-card">
      <h3>{t.tests}</h3>
      <Row title={t.command} help={t.commandHelp}>
        <div className="language-segment verify-segment" role="group" aria-label={t.command}>
          <button type="button" aria-pressed={mode === "auto"} data-testid="test-mode-auto"
            onClick={() => choose("auto")}>{t.auto}</button>
          <button type="button" aria-pressed={mode === "custom"} data-testid="test-mode-custom"
            onClick={() => choose("custom")}>{t.custom}</button>
        </div>
      </Row>
      <Row title={t.detected} help={label.evidence ?? undefined}>
        {label.command
          ? <code className="verify-command" dir="ltr" data-testid="test-detected">{label.command}</code>
          : <span className="muted" data-testid="test-detected">{label.empty}</span>}
      </Row>
      <Row title={t.customCommand} help={t.customHelp}>
        <input type="text" dir="ltr" className="verify-text" data-testid="test-command" aria-label={t.customCommand}
          value={verify?.command ?? ""} disabled={mode === "auto"}
          onChange={event => {
            setChoice("custom");
            change(withVerify(value, { command: event.target.value }));
          }} />
      </Row>
      <Row title={t.gate} help={t.gateHelp}>
        <Switch checked={verify?.gate ?? true} label={t.gate} testId="verify-gate"
          onChange={next => change(withVerify(value, { gate: next }))} />
      </Row>
    </section>
    <SaveBar saving={settings.saving || settings.approval?.status === "pending"} error={settings.error} saved={saved}
      copy={t} onSave={() => { setSaved(true); void settings.save(); }} />
    {settings.approval && <><p role="status">{t.review}</p><ApprovalCard record={settings.approval} locale={session.locale} inline /></>}
  </div>;
}
