"use client";
import { useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import type { Locale } from "../../i18n";
import type { SkillDetail, SkillRecord } from "../../lib/protocol";
import { badgeOf, scanOk, skillSource, tokenLabel } from "../../lib/skills";
import { localeDigits } from "../../lib/localised-number";

function badgeText(skill: SkillRecord, copy: CustomizeCopy): string {
  const badge = badgeOf(skill);
  if (badge === "blocked") return copy.blocked;
  if (badge === "broken") return copy.broken;
  if (badge === "fromProject") return copy.fromProject;
  if (badge === "needsApproval") return copy.needsApproval;
  return copy.ready;
}

export function SkillCard({ skill, active, copy, locale, onSelect, onToggle, disabled }: {
  skill: SkillRecord; active: boolean; copy: CustomizeCopy; locale: Locale;
  onSelect(): void; onToggle(): void; disabled: boolean;
}) {
  const badge = badgeOf(skill);
  return <article className={`skill-card ${active ? "active" : ""}`} data-testid={`skill-card-${skill.name}`}>
    <button className="skill-card-main" onClick={onSelect} aria-pressed={active}>
      <span className="skill-card-head">
        <b dir="ltr">{skill.name}</b>
        <span className={`skill-badge ${badge}`}>{badgeText(skill, copy)}</span>
      </span>
      <span className="skill-card-description">{skill.description}</span>
      <span className="skill-card-tags">
        {skill.command && <code dir="ltr">{skill.command}</code>}
        {skill.requires_approval && badge !== "needsApproval" && <span className="skill-badge needsApproval">{copy.needsApproval}</span>}
      </span>
    </button>
    <footer className="skill-card-footer">
      <span className="muted" data-testid={`skill-scan-${skill.name}`}>
        {scanOk(skill) ? copy.scanClean : copy.scanFlagged} · {tokenLabel(skill.tokens, locale)} {copy.tokens}
      </span>
      <button
        role="switch"
        aria-checked={Boolean(skill.enabled)}
        aria-label={`${copy.enable} ${skill.name}`}
        data-testid={`skill-switch-${skill.name}`}
        className={`switch ${skill.enabled ? "on" : ""}`}
        disabled={disabled}
        onClick={onToggle}
      ><span /></button>
    </footer>
  </article>;
}

export function SkillDetailPanel({ detail, copy, locale, canEdit, onEdit, onRemove, onToggle, busy, problem }: {
  detail: SkillDetail | null; copy: CustomizeCopy; locale: Locale; canEdit: boolean;
  onEdit(): void; onRemove(): void; onToggle(): void; busy: boolean; problem?: string | null;
}) {
  if (!detail) return <aside className="skill-detail empty"><p className="muted">{copy.select}</p></aside>;
  const scripts = detail.scan?.scripts ?? [];
  const source = detail.source === "workspace" ? copy.fromProject : detail.source === "bundled" ? copy.ready : copy.mine;
  return <aside className="skill-detail" data-testid="skill-detail">
    <div className="skill-detail-head">
      <b dir="ltr">{detail.name}</b>
      <button
        role="switch"
        aria-checked={Boolean(detail.enabled)}
        aria-label={copy.enabledIn}
        className={`switch ${detail.enabled ? "on" : ""}`}
        disabled={busy}
        onClick={onToggle}
      ><span /></button>
    </div>
    <p className="muted">{detail.description}</p>
    <dl className="skill-facts">
      <div><dt>{copy.command}</dt><dd dir="ltr">{detail.command ?? copy.none}</dd></div>
      <div><dt>{copy.source}</dt><dd>{source}</dd></div>
      <div><dt>{copy.scriptsLabel}</dt><dd>{scripts.length ? scripts.join(", ") : copy.none}</dd></div>
      <div><dt>{copy.contextCost}</dt><dd>{tokenLabel(detail.tokens, locale)} {copy.tokens}</dd></div>
    </dl>
    {(problem || detail.problem) && <p className="error" role="alert">{problem ?? detail.problem}</p>}
    <b>SKILL.md</b>
    <pre dir="ltr" className="skill-source" data-testid="skill-source">{skillSource(detail)}</pre>
    <div className="skill-detail-actions">
      <button onClick={onEdit} disabled={busy || !canEdit} title={canEdit ? undefined : copy.builtInReadOnly}>{copy.edit}</button>
      <button className="danger" onClick={onRemove} disabled={busy || !canEdit}>{copy.remove}</button>
    </div>
  </aside>;
}

export function enabledLabel(count: number, locale: Locale): string {
  return localeDigits(count, locale);
}
