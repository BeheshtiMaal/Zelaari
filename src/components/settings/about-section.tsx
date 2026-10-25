"use client";
import { useEffect, useState } from "react";
import { settingsCopy } from "../../i18n/settings";
import { connection, type AppInfo } from "../../lib/desktop";
import { fillText } from "../../lib/errors";
import type { Session } from "../../lib/use-session";
import { Row } from "./verify-rows";

/**
 * About.
 *
 * The version shown is the one the engine reports, not a constant in the bundle, so the card
 * cannot claim a version this build is not running. "Check manually" says the same thing
 * because there is no update channel: it reports the running version instead of pretending
 * to look for a newer one.
 */
export function AboutSection({ session }: { session: Session }) {
  const t = settingsCopy(session.locale).about;
  const [info, setInfo] = useState<AppInfo | null>(null), [checked, setChecked] = useState("");
  useEffect(() => {
    let live = true;
    async function load() {
      try { const value = await connection()?.appInfo(); if (live) setInfo(value ?? null); }
      catch { if (live) setInfo(null); }
    }
    void load();
    return () => { live = false; };
  }, []);
  const version = info?.version ?? "—";
  return <>
    <section className="model-card" data-testid="about-app">
      <h3>{t.version}</h3>
      <Row title={t.version}><code className="verify-command" dir="ltr" data-testid="about-version">{version}</code></Row>
      <Row title={t.licence}><code className="verify-command" dir="ltr">{info ? "MIT" : "—"}</code></Row>
      <Row title={t.built}>{t.builtValue}</Row>
    </section>
    <section className="model-card" data-testid="about-limits">
      <h3>{t.updates}</h3>
      <Row title={t.updates} help={t.updatesValue}>
        <button className="light-button" data-testid="about-check" disabled={!info}
          onClick={() => setChecked(fillText(t.checkResult, { version }))}>{t.check}</button>
      </Row>
      {checked && <p className="muted" role="status" data-testid="about-check-result">{checked}</p>}
      <Row title={t.logs} help={t.logsValue}>
        <div className="data-path">
          {info && <code dir="ltr">{info.logDirectory}</code>}
          <button className="light-button" data-testid="about-logs" disabled={!info}
            onClick={() => void connection()?.openLogFolder()}>{t.openLogs}</button>
        </div>
      </Row>
    </section>
    <section className="model-card" data-testid="about-isolation">
      <h3>{t.isolation}</h3>
      <p className="muted">{t.isolationValue}</p>
      <Row title={t.security}><code className="verify-command" dir="ltr">SECURITY.md</code></Row>
    </section>
  </>;
}
