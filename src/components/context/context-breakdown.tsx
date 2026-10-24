import type { Locale } from "../../i18n";
import { contextCopy } from "../../i18n/context";
import { barShare, compactTokens, percentLabel, usedPercent } from "../../lib/context-format";
import type { ContextUpdated } from "../../lib/protocol";

export function ContextBreakdown({ event, locale, threshold, summary, busy, onNewChat }: {
  event: ContextUpdated;
  locale: Locale;
  threshold: number;
  summary: boolean;
  busy: boolean;
  onNewChat?(): void;
}) {
  const t = contextCopy(locale), measured = event.breakdown;
  const window = event.context_window ?? null;
  const rows = measured ? [
    { id: "messages", label: t.messages, value: measured.messages },
    { id: "tool_results", label: t.toolResults, value: measured.tool_results },
    { id: "system", label: t.system, value: measured.system },
    { id: "skills", label: t.skills, value: measured.skills },
    { id: "memory", label: t.memory, value: measured.memory },
  ] : [];
  const total = measured ? rows.reduce((sum, row) => sum + row.value, 0) : 0;
  const fraction = usedPercent(event.input_tokens, window);
  const marked = Math.min(1, Math.max(0, threshold / 100));
  return <div className="context-breakdown">
    <div className="context-heading"><strong>{t.title}</strong>{event.estimated && <span className="context-badge">{t.estimate}</span>}</div>
    {measured ? <>
      <div className="context-meter" role="img" aria-label={`${percentLabel(fraction, locale)} ${t.ring}`}>
        <div className="context-meter-fill" style={{ inlineSize: `${fraction * 100}%` }} />
        <span className="context-marker" data-testid="context-threshold" data-percent={marked * 100} style={{ insetInlineStart: `${marked * 100}%` }} title={t.threshold} />
      </div>
      <ul className="context-rows">
        {rows.map(row => <li key={row.id} data-testid={`context-row-${row.id}`}>
          <span className="context-row-label">{row.label}</span>
          <span className="context-row-value">{event.estimated ? "~" : ""}{compactTokens(row.value, locale)}</span>
          <span className="context-row-bar" aria-hidden="true"><span style={{ inlineSize: `${barShare(row.value, total) * 100}%` }} /></span>
        </li>)}
      </ul>
      <p className="context-total" data-testid="context-total">
        <span>{t.total}</span>
        <span dir="ltr">{event.estimated ? "~" : ""}{compactTokens(event.input_tokens, locale)} / {event.context_window_estimated ? "~" : ""}{window ? compactTokens(window, locale) : "—"}</span>
      </p>
      <p className="context-threshold-copy">{t.threshold} · {percentLabel(marked, locale)}</p>
    </> : <p className="muted">{t.unavailable}</p>}
    <button type="button" className="context-new-chat" data-testid="context-new-chat" disabled={!summary || busy} onClick={onNewChat}>{t.newChat}</button>
    <p className="context-help">{summary ? t.newChatHelp : t.unavailable}</p>
  </div>;
}
