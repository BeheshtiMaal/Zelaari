"use client";
import { useState } from "react";
import { settingsCopy } from "../../i18n/settings";
import { fill, fillText } from "../../lib/errors";
import { confirmFacts, describeKeys, describeRuns, type ConfirmKind } from "../../lib/confirm";
import { connection } from "../../lib/desktop";
import { useData } from "../../lib/use-data";
import { useSkills } from "../../lib/use-skills";
import type { Session } from "../../lib/use-session";
import { ConfirmDialog } from "./confirm-dialog";
import { Row, Switch } from "./verify-rows";

const RETENTIONS = [7, 30, 90, 0];

export function DataSection({ session }: { session: Session }) {
  const t = settingsCopy(session.locale).data, data = useData(session.workspace), skills = useSkills(session.workspace);
  const [dialog, setDialog] = useState<ConfirmKind | null>(null);
  const [failed, setFailed] = useState(false), [notice, setNotice] = useState("");
  const facts = confirmFacts(data.summary, session.workspace);
  const search = skills.skills.find(skill => skill.name === "web-search");
  const appData = data.summary?.app_data ?? "";
  const stored = session.settings.retention_days ?? 30;
  const count = new Intl.NumberFormat(session.locale);
  // The engine accepts any day count, so a value that is not one of the four choices is still
  // offered as itself rather than silently reading as "30 days". Zero means forever, so it sorts
  // last rather than first.
  const rank = (value: number) => (value === 0 ? Number.POSITIVE_INFINITY : value);
  const choices = RETENTIONS.includes(stored) ? RETENTIONS : [...RETENTIONS, stored].sort((a, b) => rank(a) - rank(b));
  const days = (value: number) => {
    const index = RETENTIONS.indexOf(value);
    return index >= 0 ? t.retentions[index] : fillText(t.days, { days: count.format(value) });
  };
  const chooseRetention = (value: number) => { void session.changeSettings({ ...session.settings, retention_days: value }); };
  async function clearRuns(): Promise<boolean> {
    setFailed(false);
    const result = await data.clearRuns();
    if (!result) { setFailed(true); return false; }
    setNotice(fill(t.cleared, { runs: result.runs ?? 0 }, session.locale));
    return true;
  }
  async function clearKeys(): Promise<boolean> {
    setFailed(false);
    const result = await connection()?.clearKeys();
    if (!result?.ok) { setFailed(true); return false; }
    setNotice(fill(t.keysCleared, { keys: result.keys }, session.locale));
    await session.reloadModels();
    return true;
  }
  const open = dialog === "runs" ? clearRuns : clearKeys;
  return <>
    <section className="model-card" data-testid="data-location">
      <h3>{t.where}</h3>
      <Row title={t.appData} help={t.appDataHelp}>
        <div className="data-path">
          <code dir="ltr">{appData || "—"}</code>
          <button className="light-button" disabled={!appData} onClick={() => void connection()?.revealAppData()}>{t.open}</button>
        </div>
      </Row>
      <Row title={t.project} help={t.projectHelp}>
        <code dir="ltr">{facts.harness ? ".harness/" : "—"}</code>
      </Row>
      <Row title={t.retention} help={t.retentionHelp}>
        <select className="verify-select" aria-label={t.retention} value={stored} data-testid="retention-select"
          onChange={event => chooseRetention(Number(event.target.value))}>
          {choices.map(value => <option key={value} value={value}>{days(value)}</option>)}
        </select>
      </Row>
    </section>
    <section className="model-card" data-testid="data-privacy">
      <h3>{t.privacy}</h3>
      <Row title={t.sent} help={t.sentHelp}><span className="verify-badge">{t.zero}</span></Row>
      <Row title={t.webSearch} help={search ? t.webSearchHelp : t.webSearchMissing}>
        <Switch checked={search?.enabled ?? false} label={t.webSearch} testId="web-search-switch" disabled={!search}
          onChange={() => void skills.toggle({ name: "web-search", enabled: search?.enabled })} />
      </Row>
    </section>
    <section className="model-card danger-zone" data-testid="data-danger">
      <h3>{t.danger}</h3>
      <Row title={t.clearRuns} help={session.workspace ? describeRuns(t.runsCount, facts, session.locale) : t.noWorkspace}>
        <button className="danger-button" disabled={!session.workspace || data.busy} onClick={() => { setNotice(""); setDialog("runs"); }}>{t.clearRunsAction}</button>
      </Row>
      <Row title={t.deleteKeys} help={describeKeys(t.keysCount, facts, session.locale)}>
        <button className="danger-button" disabled={!facts.keys} onClick={() => { setNotice(""); setDialog("keys"); }}>{t.deleteKeysAction}</button>
      </Row>
      {data.error && <p className="error" role="alert">{t.failed}</p>}
      {notice && <p className="muted" role="status" data-testid="data-notice">{notice}</p>}
    </section>
    {dialog && <ConfirmDialog title={dialog === "runs" ? t.confirmRunsTitle : t.confirmKeysTitle}
      description={dialog === "runs" ? t.confirmRunsBody : t.confirmKeysBody}
      effects={dialog === "runs"
        ? [describeRuns(t.runsCount, facts, session.locale), facts.harness]
        : [describeKeys(t.keysCount, facts, session.locale)]}
      acknowledge={t.acknowledge} confirmLabel={t.confirm} cancelLabel={t.cancel}
      busy={dialog === "runs" ? data.busy : false} failed={failed} errorLabel={t.failed}
      close={() => { setDialog(null); setFailed(false); }} onConfirm={open} />}
  </>;
}
