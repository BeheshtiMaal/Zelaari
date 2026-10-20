"use client";
import { useEffect, type ReactNode } from "react";
import type { Locale } from "../../i18n";
import { planningCopy } from "../../i18n/planning";
import type { ActivityScope, HarnessEvent } from "../../lib/protocol";
import { eventBodyModel, thinkingState, timelineGroups } from "../../lib/timeline";
import { disclosureValue, useDisclosure } from "../../lib/use-disclosure";
import type { RunState } from "../../store/run";
import { Message } from "../../genui/message";
import { ToolErrorCard } from "../tool-error-card";
import { toolFailure } from "../../lib/errors";
import { dictionary } from "../../i18n";

export function Disclosure({ id, active, terminal, title, children, className = "" }: { id: string; active: boolean; terminal: boolean; title: ReactNode; children: ReactNode; className?: string }) {
  const values = useDisclosure(state => state.values), toggle = useDisclosure(state => state.toggle);
  const previous = values[id], value = disclosureValue(previous, active, terminal);
  useEffect(() => { if (value !== previous) toggle(id, value); }, [id, value.open, value.ended, previous, toggle]);
  return <section className={`activity-disclosure ${className}`}>
    <button type="button" className="disclosure-button" aria-expanded={value.open} aria-controls={`body-${id}`} onClick={() => toggle(id, { ...value, open: !value.open })}><span className="disclosure-caret" aria-hidden="true">›</span>{title}</button>
    <div id={`body-${id}`} hidden={!value.open}>{children}</div>
  </section>;
}

function Thinking({ scope, events, locale, runId }: { scope: ActivityScope; events: HarnessEvent[]; locale: Locale; runId: string }) {
  const t = planningCopy(locale);
  const { finished, reasoning } = thinkingState(scope, events);
  return <Disclosure id={`${runId}-thinking-${scope.scope_id}`} active={!finished} terminal={finished} className="thinking-panel" title={<><strong>{t.thinking}</strong><span className="muted" dir="auto">{scope.provider ? `${scope.provider} · ` : ""}{scope.model}</span></>}>
    <div className="thinking-body" dir="auto">{reasoning || (finished ? t.noReason : t.awaiting)}{!finished && reasoning && <span className="streaming-caret" aria-hidden="true">▍</span>}</div>
  </Disclosure>;
}

function EventBody({ events, locale, runId, child = false, retry }: { events: HarnessEvent[]; locale: Locale; runId: string; child?: boolean; retry?: (command: string) => void }) {
  const { turns, tools, messages } = eventBodyModel(events, child);
  return <div className="step-body">
    {turns.map(event => <Thinking key={event.scope.scope_id} scope={event.scope} events={events} locale={locale} runId={runId} />)}
    {tools.map(({ event, result }) => {
      if (result?.type === "tool.result" && toolFailure(result.text)) return <ToolErrorCard key={`${event.scope?.scope_id}-${event.call_id}`} text={result.text} t={dictionary(locale)} locale={locale} command={typeof event.args.command === "string" ? event.args.command : undefined} onRetry={retry ?? (() => undefined)} />;
      return <details className="tool-line" key={`${event.scope?.scope_id}-${event.call_id}`} data-testid="tool-line"><summary><span className="status-dot" /><code dir="ltr">{event.name} · {String(event.args.file_path ?? event.args.command ?? "")}</code></summary><pre className="readable" dir="auto">{result?.type === "tool.result" ? result.text : "…"}</pre></details>;
    })}
    {messages.map(message => <Message key={message.id} text={message.text} streaming={false} />)}
  </div>;
}

export function ActivityTimeline({ run, locale, retry }: { run: RunState; locale: Locale; retry?: (command: string) => void }) {
  const t = planningCopy(locale), number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  return <div className="activity-timeline">{timelineGroups(run).map(group => {
    const { events, progress, active, terminal, elapsed, counts, children } = group;
    return <Disclosure key={group.id ?? "analysis"} id={`${run.runId}-step-${group.id ?? "analysis"}`} active={active} terminal={terminal} className={`step-card ${active && run.status === "running" ? "active" : ""}`} title={<><span className="step-mark" aria-hidden="true">{progress?.status === "completed" ? "✓" : "○"}</span><strong>{group.title ?? t.analysis}</strong><span className="step-summary">{elapsed !== null && `${number.format(elapsed)} ${t.seconds} · `}{number.format(counts.read)} {t.read} · {number.format(counts.writes)} {t.writes} · {number.format(counts.commands)} {t.commands}{terminal && group.reasoningFinished && <small className="reasoning-note">{group.reasoningAvailable ? t.thinking : t.noReason}</small>}</span></>}>
      <EventBody events={events} locale={locale} runId={run.runId ?? "history"} retry={retry} />
      {children.map(({ child, end, events: childEvents, seconds }) => {
        return <Disclosure key={child.scope.scope_id} id={`${run.runId}-child-${child.scope.scope_id}`} active={!end} terminal={!!end} className="delegate-card" title={<><strong>{t[child.scope.agent === "reviewer" ? "reviewer" : "researcher"]}</strong><span className="read-only-badge">{t.readOnly}</span><span className="muted">{end?.type === "subagent.finished" ? t[end.status] : t.running}{seconds !== null && ` · ${number.format(seconds)} ${t.seconds}`}</span></>}><p dir="auto">{child.task}</p><EventBody events={childEvents} locale={locale} runId={run.runId ?? "history"} child />{end?.type === "subagent.finished" && end.result && <pre className="readable" dir="auto">{end.result}</pre>}</Disclosure>;
      })}
      {group.summaries.map(event => <p key={event.operation_id} className="summary-notice">{t.summary}{event.affected_messages ? ` · ${number.format(event.affected_messages)} ${t.messages}` : ""}</p>)}
    </Disclosure>;
  })}</div>;
}
