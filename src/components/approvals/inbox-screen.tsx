"use client";
import { useState, useRef, type KeyboardEvent } from "react";
import { FileIcon } from "@phosphor-icons/react/dist/csr/File";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import type { Locale } from "../../i18n";
import { approvalCopy } from "../../i18n/approvals";
import { statesCopy } from "../../i18n/states";
import { filteredApprovals, pendingCount, recordKey, useInbox, type ApprovalStatus } from "../../lib/inbox";
import { resolve } from "../../lib/shortcuts";
import { EmptyState } from "../states/empty-state";
import { ApprovalCard } from "./approval-card";

export function InboxScreen({ locale, onHome }: { locale: Locale; onHome?(): void }) {
  const t = approvalCopy(locale), inbox = useInbox(), states = statesCopy(locale);
  const [tab, setTab] = useState<ApprovalStatus>("pending"), [selected, setSelected] = useState<string | null>(() => typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("approval"));
  const rows = filteredApprovals(inbox.records, tab), count = pendingCount(inbox.records);
  const active = inbox.records.find(record => recordKey(record.request) === selected) ?? rows[0];
  const recent = tab === "pending" ? filteredApprovals(inbox.records, "all").filter(record => record.status !== "pending").slice(0, 5) : [];
  const list = useRef<HTMLDivElement>(null);
  // Arrows move the selection, and the focus follows it so the next key lands in the list.
  function move(event: KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    const hit = resolve("inbox", { key: event.key, tag: target.tagName, contentEditable: target.isContentEditable });
    if (!hit) return;
    event.preventDefault();
    const at = rows.findIndex(record => active && recordKey(record.request) === recordKey(active.request));
    const next = rows[Math.min(rows.length - 1, Math.max(0, at < 0 ? 0 : at + (hit.action === "next" ? 1 : -1)))];
    if (!next) return;
    const key = recordKey(next.request);
    setSelected(key);
    list.current?.querySelector<HTMLElement>(`[data-approval="${CSS.escape(key)}"]`)?.focus();
  }
  function row(record: typeof inbox.records[number]) {
    const request = record.request, key = recordKey(request);
    return <button key={key} className={`inbox-row ${active && recordKey(active.request) === key ? "selected" : ""} ${record.status !== "pending" ? "decided" : ""}`} onClick={() => setSelected(key)} aria-pressed={!!active && recordKey(active.request) === key} data-approval={key}>
      <div className="inbox-row-heading">{request.kind === "command" ? <ShieldCheckIcon size={18} /> : <FileIcon size={18} />}<strong>{request.tool === "rules_update" ? t.rules : request.kind === "command" ? t.command : t.file} <bdi>{request.path}</bdi></strong><time dateTime={request.created_at}>{request.created_at && new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(new Date(request.created_at))}</time></div>
      <p className="muted">{request.source_kind === "schedule" ? t.schedule : request.source_kind === "configuration" ? t.configuration : t.task}: {request.source_title}</p>
      {request.command && <pre dir="ltr" className="command-preview">{request.command}</pre>}
      <span className={`risk-badge ${request.risk?.level ?? "low"} ${record.status ?? "pending"}`}>{record.status === "pending" ? request.risk?.level === "high" ? t.high : t.low : t[record.status ?? "pending"]}</span>
    </button>;
  }
  return <div className="inbox-screen">
    <header className="inbox-heading"><div><h1>{t.title}</h1><p className="muted">{new Intl.NumberFormat(locale).format(count)} {t.waiting}</p></div><div className="inbox-tabs" role="tablist" aria-label={t.title}>
      {(["pending", "approved", "rejected", "all"] as const).map(value => <button key={value} role="tab" aria-selected={tab === value} onClick={() => { setTab(value); setSelected(null); }}>{t[value]}{value === "pending" ? ` (${new Intl.NumberFormat(locale).format(count)})` : ""}</button>)}
    </div></header>
    {inbox.failed && <p role="alert" className="error">{t.error} <button onClick={() => void inbox.refresh()}>{t.refresh}</button></p>}
    {!inbox.records.length ? <EmptyState testId="state-empty-inbox" icon={<ShieldCheckIcon size={26} />}
      label={states.emptyInbox.label} title={states.emptyInbox.title} help={states.emptyInbox.help}
      actions={onHome ? [{ label: states.emptyInbox.primary, testId: "state-back-home", primary: true, onClick: onHome }] : []} /> :
    <div className="inbox-panes"><div className="inbox-list" ref={list} onKeyDown={move} role="group" aria-label={t.title}>{rows.map(row)}{!rows.length && <p className="muted">{t.empty}</p>}{recent.length > 0 && <><p className="muted">{t.recent}</p>{recent.map(row)}</>}</div>
      <div className="inbox-detail">{active ? <ApprovalCard key={recordKey(active.request)} record={active} locale={locale} /> : <p className="muted">{t.select}</p>}</div>
    </div>}
  </div>;
}
