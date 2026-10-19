"use client";
import { useState } from "react";
import type { Dictionary } from "../i18n";
import { commandTimeout, fill, jailBlock } from "../lib/errors";

/**
 * The two Phase 3 error cards (R30, R31). Both keep the raw tool output one click
 * away, because the card is a summary and the person may need the detail.
 */
export function ToolErrorCard({ text, t, locale, onRetry }: {
  t: Dictionary; text: string; locale: string; onRetry(command: string): void;
}) {
  const [dismissed, setDismissed] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const timeout = commandTimeout(text);
  const block = jailBlock(text);
  if (dismissed || (!timeout && !block)) return null;

  if (timeout) {
    return <section className="tool-error-card" data-testid="timeout-card">
      <div className="tool-error-head">
        <b>{fill(t.timeoutTitle, { seconds: timeout.seconds }, locale)}</b>
        <span className="tool-error-tag">{t.timeoutTag}</span>
      </div>
      <p>{t.timeoutNote}</p>
      <div className="tool-error-actions">
        <button type="button" className="light-button" data-testid="timeout-retry" onClick={() => onRetry(timeout.command)}>
          {fill(t.timeoutAction, { seconds: 300 }, locale)}
        </button>
        <button type="button" className="danger-outline" data-testid="timeout-reject" onClick={() => setDismissed(true)}>{t.reject}</button>
      </div>
      <pre className="tool-error-command" dir="ltr">{`$ ${timeout.command}\n${fill(t.timeoutDetail, { seconds: timeout.seconds }, locale)}`}</pre>
      <p className="tool-error-hint">{t.timeoutHint}</p>
    </section>;
  }

  if (!block) return null;
  return <section className="tool-error-card amber" data-testid="jail-card">
    <div className="tool-error-head">
      <b>{t.jailTitle}</b>
      <span className="tool-error-tag">{t.jailTag}</span>
    </div>
    <p>{t.jailNote}</p>
    <p className="tool-error-never">{t.jailNever}</p>
    <div className="tool-error-actions">
      <button type="button" onClick={() => setShowRaw(value => !value)} aria-expanded={showRaw}>{t.jailDetail}</button>
    </div>
    <pre className="tool-error-command" dir="ltr">{block.path}</pre>
    {showRaw && <pre className="tool-error-raw" dir="ltr">{text}</pre>}
    <p className="tool-error-hint">{t.jailHint}</p>
  </section>;
}
