"use client";
import { useEffect, useRef } from "react";
import type { Locale } from "../../i18n";
import { questionCopy } from "../../i18n/questions";
import type { QuestionRecord } from "../../lib/protocol";
import { answeredSummary, editableTarget, questionDigit } from "../../lib/questions";
import { useQuestionEditor, useQuestionStore } from "../../lib/use-questions";
import { useRun } from "../../store/run";

export function QuestionCard({ record, locale }: { record: QuestionRecord; locale: Locale }) {
  const e = useQuestionEditor(record), t = questionCopy(locale), root = useRef<HTMLElement>(null);
  const format = (value: number) => new Intl.NumberFormat(locale).format(value);
  const previousIndex = useRef(e.index);
  useEffect(() => { if (previousIndex.current !== e.index) root.current?.querySelector<HTMLElement>("legend")?.focus(); previousIndex.current = e.index; }, [e.index]);
  const q = e.question, chosen = e.selection.option_ids ?? [], pending = record.status === "pending";
  const ranked = q.type === "rank" ? chosen.map(id => q.options.find(option => option.id === id)!) : q.options;
  const exhausted = record.request.presentation === "exhausted";
  const label = (id: string, fallback: string) => exhausted ? ({ retry: t.retry, change: t.change, stop: t.stop }[id] ?? fallback) : fallback;
  return <section ref={root} className={`question-card ${exhausted ? "question-exhausted" : ""} ${pending ? "" : "question-history"}`} tabIndex={0} data-testid="question-card" onKeyDown={event => {
    if (!pending || e.busy || event.nativeEvent.isComposing || editableTarget(event.target) || event.altKey || event.ctrlKey || event.metaKey) return;
    const digit = questionDigit(event.key, event.code);
    if (digit >= 1 && digit <= q.options.length) { event.preventDefault(); if (q.type === "rank") root.current?.querySelector<HTMLElement>(`[data-rank="${q.options[digit - 1].id}"] button:not(:disabled)`)?.focus(); else e.choose(q.options[digit - 1].id); }
    if (digit === q.options.length + 1 && digit <= 4) { event.preventDefault(); e.other(""); root.current?.querySelector<HTMLInputElement>("input[type=text]")?.focus(); }
    if (event.key === "Enter" && !(event.target as HTMLElement).closest("button")) { event.preventDefault(); e.advance(); }
    if (event.key === "Escape") { event.preventDefault(); void e.send(true); }
  }}>
    <div className="question-heading"><span dir="auto">{exhausted && record.request.failure ? `${format(record.request.failure.attempts)} ${t.failedAttempts}` : q.header}</span><small>{record.request.failure?.step} {t.question} {format(e.index + 1)} {t.of} {format(record.request.questions.length)}</small></div>
    {record.request.failure && <pre className="question-failure" dir="ltr">{record.request.failure.output}</pre>}
    {record.request.context && <pre className="question-context" dir="auto">{record.request.context}</pre>}
    {pending ? <><fieldset disabled={e.busy}><legend tabIndex={-1} dir="auto">{q.text}</legend>
      <div className="question-options">{ranked.map((option, i) => q.type === "rank" ?
        <div className="question-option question-rank" key={option.id} data-rank={option.id} draggable={!e.busy}
          onDragStart={event => event.dataTransfer.setData("text/plain", option.id)} onDragOver={event => event.preventDefault()}
          onDrop={event => { event.preventDefault(); e.drop(event.dataTransfer.getData("text/plain"), option.id); }}>
          <span aria-hidden="true">⠿ {format(i + 1)}</span><span><b>{option.label}</b><small>{option.description}</small></span>
          <div className="rank-controls"><button type="button" aria-label={`${t.moveUp}: ${option.label}`} disabled={i === 0 || e.busy} onClick={() => e.move(option.id, -1)}>↑</button><button type="button" aria-label={`${t.moveDown}: ${option.label}`} disabled={i === ranked.length - 1 || e.busy} onClick={() => e.move(option.id, 1)}>↓</button></div>
        </div> : <label className={`question-option ${chosen.includes(option.id) ? "selected" : ""}`} key={option.id}>
          <input type={q.type === "multi" ? "checkbox" : "radio"} name={`${record.request.call_id}-${q.id}`} checked={chosen.includes(option.id)} onChange={() => e.choose(option.id)} aria-describedby={`${record.request.call_id}-${q.id}-${option.id}`} />
          <span><b>{format(i + 1)} · {label(option.id, option.label)}</b><small id={`${record.request.call_id}-${q.id}-${option.id}`}>{option.description}</small></span>
        </label>)}
        <label className={`question-option ${e.selection.other !== null && e.selection.other !== undefined ? "selected" : ""}`}>
          {q.type !== "rank" && <input type={q.type === "multi" ? "checkbox" : "radio"} name={`${record.request.call_id}-${q.id}`} aria-label={t.other} checked={e.selection.other !== null && e.selection.other !== undefined} onChange={() => e.other(e.selection.other === null || e.selection.other === undefined ? "" : null)} />}
          <input type="text" maxLength={4000} aria-label={t.other} placeholder={t.other} value={e.selection.other ?? ""} onChange={event => e.other(event.target.value || null)} />
        </label>
      </div>
      {exhausted && chosen.includes("retry") && <label className="question-hint">{t.hint}<textarea aria-label={t.hint} maxLength={4000} value={e.selection.hint ?? ""} onChange={event => e.hint(event.target.value)} /></label>}
    </fieldset>
    {e.invalid && <p className="error" role="alert">{t.required}</p>}{e.error && <p className="error" role="alert">{t.error}</p>}
    <span className="sr-only" aria-live="polite">{t.order}: {e.announcement}</span>
    <div className="question-footer"><small>{format(1)} {t.range} {format(Math.min(4, q.options.length + 1))} {t.choose} · {t.enter}</small><div className="button-row">
      <button type="button" className="question-decline" disabled={e.busy} onClick={() => void e.send(true)}>{t.decline}</button>
      {e.index > 0 && <button type="button" disabled={e.busy} onClick={e.back}>{t.back}</button>}
      <button type="button" className="question-send" disabled={e.busy} onClick={e.advance}>{e.index < record.request.questions.length - 1 ? t.next : t.send}</button>
    </div></div></> : <details><summary>{t[record.status as "answered" | "declined" | "cancelled"]}</summary>{answeredSummary(record).map(answer => <p key={answer.id} dir="auto"><b>{answer.text}</b><br />{answer.values}</p>)}</details>}
  </section>;
}

export function RegisteredQuestionCard({ runId, callId }: { runId: string; callId: string }) {
  const activeRun = useRun(state => state.runId);
  const record = useQuestionStore(state => state.records[runId]?.find(record => record.request.call_id === callId));
  if (!record || activeRun !== runId) return null;
  const locale = typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "fa";
  return <QuestionCard key={`${runId}/${callId}`} record={record} locale={locale} />;
}
