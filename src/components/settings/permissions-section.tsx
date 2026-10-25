"use client";
import { settingsCopy } from "../../i18n/settings";
import { segment } from "../../lib/appearance";
import { MODES, lockedRows, ruleRows, scopeLabel } from "../../lib/permissions-view";
import { useRules } from "../../lib/use-rules";
import type { Session } from "../../lib/use-session";
import { PlanningSettingsForm } from "./planning-settings";
import { Row, Segment } from "./verify-rows";

export function PermissionsSection({ session }: { session: Session }) {
  const t = settingsCopy(session.locale).permissions;
  const rules = useRules(session.workspace);
  const { rows: locked, assumed } = lockedRows(rules.effective?.always_ask);
  const grid = ruleRows(rules.effective);
  return <>
    <section className="model-card" data-testid="default-mode">
      <h3>{t.defaultMode}</h3>
      <Row title={t.modeRow} help={t.modeHelp}>
        <Segment label={t.modeRow} testId="default-mode-segment" options={segment(MODES, t.modes, session.settings.default_mode ?? "ask")}
          onSelect={mode => void session.changeDefaultMode(mode)} />
      </Row>
    </section>
    <PlanningSettingsForm session={session} />
    <section className="model-card" data-testid="always-ask">
      <h3>{t.alwaysAsk}</h3>
      {assumed && session.workspace && <p className="muted" role="status" data-testid="always-ask-assumed">{t.lockedAssumed}</p>}
      {locked.map(row => <Row key={row.key} title={t.conditions[row.key].title} help={t.conditions[row.key].help || row.text}>
        <span className="verify-badge locked-chip" data-testid={`locked-${row.key}`}>{t.locked}</span>
      </Row>)}
    </section>
    <section className="model-card" data-testid="rules-grid">
      <h3>{t.rules}</h3>
      {!session.workspace ? <div className="rules-empty">
        <p className="muted">{t.noWorkspace}</p>
        <button className="light-button" onClick={() => void session.pickWorkspace()}>{t.chooseFolder}</button>
      </div> : <>
        {grid.fromDefaults && <p className="muted" data-testid="rules-defaults">{t.rulesDefaults}</p>}
        <div className="rules-table"><table>
          <caption className="sr-only">{t.rules}</caption>
          <thead><tr><th scope="col">{t.rulesTool}</th><th scope="col">{t.rulesScope}</th><th scope="col">{t.rulesDecision}</th></tr></thead>
          <tbody>{grid.rows.map(row => <tr key={row.tool}>
            <td><code dir="ltr">{row.tool}</code></td>
            <td><code dir="ltr">{scopeLabel(row)}</code></td>
            <td><span className={`decision-badge ${row.action}`} data-testid={`decision-${row.tool}`}>{t.decisions[row.action]}</span></td>
          </tr>)}</tbody>
        </table></div>
        <a className="rules-edit-link" href="/customize/?tab=rules">{t.rulesEdit}</a>
      </>}
    </section>
  </>;
}
