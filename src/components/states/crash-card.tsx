"use client";
import { useEffect, useRef } from "react";
import { WarningIcon } from "@phosphor-icons/react/dist/csr/Warning";
import type { Locale } from "../../i18n";
import { statesCopy } from "../../i18n/states";

/**
 * The engine stopped, and this is the whole window until it is back.
 *
 * It says the three things an error card has to say: what happened, what is still safe,
 * and what to do. It cannot be dismissed, because there is nothing behind it that works.
 */
export function CrashCard({ locale, restarting, failed, onRestart, onLogs }: {
  locale: Locale;
  restarting: boolean;
  failed: boolean;
  onRestart(): void;
  onLogs(): void;
}) {
  const t = statesCopy(locale).crash, restart = useRef<HTMLButtonElement>(null);
  useEffect(() => { restart.current?.focus(); }, []);
  return <div className="crash-overlay" data-testid="crash-card">
    <section className="crash-card" role="alertdialog" aria-modal="true" aria-labelledby="crash-title" aria-describedby="crash-safe">
      <span className="crash-icon" aria-hidden="true"><WarningIcon size={26} /></span>
      <h2 id="crash-title">{t.title}</h2>
      <p id="crash-safe">{t.safe}</p>
      <div className="crash-actions">
        <button ref={restart} type="button" className="primary" data-testid="restart-engine"
          disabled={restarting} onClick={onRestart}>{restarting ? t.restarting : t.restart}</button>
        <button type="button" data-testid="crash-logs" onClick={onLogs}>{t.logs}</button>
      </div>
      {failed && <p className="error" role="alert" data-testid="crash-error">{t.failed}</p>}
    </section>
  </div>;
}
