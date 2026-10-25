"use client";
import { useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import type { Locale } from "../../i18n";
import type { Session } from "../../lib/use-session";
import { useSkills, type SkillsHub } from "../../lib/use-skills";
import {
  authoredSkills,
  canEdit,
  CATEGORIES,
  filterSkills,
  installedSkills,
  type CategoryFilter,
  type SkillDraft,
} from "../../lib/skills";
import { localeDigits } from "../../lib/localised-number";
import { SkillCard, SkillDetailPanel } from "./skill-card";
import { InstallDialog } from "./install-dialog";
import { CreateDialog } from "./create-dialog";
import { MarketplaceList } from "./marketplace-list";

type Inner = "installed" | "market" | "mine";

function innerSkills(hub: SkillsHub, inner: Inner) {
  return inner === "mine" ? authoredSkills(hub.skills) : installedSkills(hub.skills);
}

export function SkillsTab({ session, copy }: { session: Session; copy: CustomizeCopy }) {
  const hub = useSkills(session.workspace);
  const [inner, setInner] = useState<Inner>("installed");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [dialog, setDialog] = useState<"install" | "create" | "edit" | "delete" | null>(null);
  const locale: Locale = session.locale;
  const shown = filterSkills(innerSkills(hub, inner), query, category);
  const selected = hub.detail;

  if (!session.workspace) return <p className="muted">{copy.chooseWorkspace}</p>;

  const close = () => { setDialog(null); void hub.load(); void hub.read(hub.selected); };
  const save = async (draft: SkillDraft) => {
    const record = dialog === "edit" ? await hub.save(draft) : await hub.create(draft);
    if (record) setDialog(null);
  };

  return <div className="skills-layout">
    <section className="skills-main">
      <div className="customize-subtabs" role="tablist">
        <button role="tab" aria-selected={inner === "installed"} data-testid="skills-tab-installed"
          onClick={() => setInner("installed")}>
          {copy.installed} ({localeDigits(installedSkills(hub.skills).length, locale)})
        </button>
        <button role="tab" aria-selected={inner === "market"} data-testid="skills-tab-market"
          onClick={() => { setInner("market"); if (!hub.market) void hub.readMarket(); }}>
          {copy.marketplace}
        </button>
        <button role="tab" aria-selected={inner === "mine"} data-testid="skills-tab-mine"
          onClick={() => setInner("mine")}>
          {copy.mine}
        </button>
      </div>

      {inner === "market" ? <MarketplaceList
        catalog={hub.market} copy={copy} busy={hub.busy}
        onCatalog={url => hub.setCatalog(url)}
        onInstall={async url => { await hub.install("git", url); }}
      /> : <>
        <div className="skills-filter">
          <input type="search" aria-label={copy.search} placeholder={copy.search} data-testid="skill-search"
            value={query} onChange={event => setQuery(event.target.value)} />
          <div className="chips">
            {CATEGORIES.map(item => <button key={item} className={category === item ? "chip active" : "chip"}
              aria-pressed={category === item} onClick={() => setCategory(item)}>{copy[item]}</button>)}
          </div>
        </div>

        {hub.error && <p className="error" role="alert">{copy.error}</p>}

        <div className="skill-grid">
          {shown.map(skill => <SkillCard key={skill.name} skill={skill} copy={copy} locale={locale}
            active={hub.selected === skill.name} disabled={hub.busy}
            onSelect={() => hub.select(skill.name)} onToggle={() => void hub.toggle(skill)} />)}
          {!shown.length && <p className="muted">{copy.empty}</p>}
          <button className="skill-add" data-testid="skill-add" onClick={() => setDialog("install")}>
            <b>{copy.addSkill}</b><span>{copy.addSkillHint}</span>
          </button>
        </div>

        {hub.problems.length > 0 && <section className="skill-problems">
          <h3>{copy.broken}</h3>
          {hub.problems.map(skill => <p key={skill.name} className="muted" dir="ltr">{skill.name}: {skill.problem}</p>)}
        </section>}
      </>}
    </section>

    <SkillDetailPanel
      detail={selected} copy={copy} locale={locale} busy={hub.busy}
      canEdit={canEdit(selected)}
      problem={null}
      onEdit={() => setDialog("edit")}
      onRemove={() => setDialog("delete")}
      onToggle={() => { if (selected) void hub.toggle(selected); }}
    />

    {dialog === "install" && <InstallDialog copy={copy} busy={hub.busy} staged={Boolean(hub.proposal)}
      onInstall={(kind, source) => hub.install(kind, source)} close={close} />}
    {(dialog === "create" || dialog === "edit") && <CreateDialog copy={copy} busy={hub.busy}
      staged={Boolean(hub.proposal)} existing={dialog === "edit" ? selected : null}
      onSave={save} close={close} />}
    {dialog === "delete" && selected && <ConfirmDelete copy={copy} busy={hub.busy}
      onConfirm={() => void hub.remove(selected.name).then(record => { if (record) setDialog(null); })}
      close={close} />}
  </div>;
}

function ConfirmDelete({ copy, busy, onConfirm, close }: {
  copy: CustomizeCopy; busy: boolean; onConfirm(): void; close(): void;
}) {
  return <div className="confirm-delete" role="dialog" aria-label={copy.deleteTitle} data-testid="delete-dialog">
    <b>{copy.deleteTitle}</b>
    <p className="muted">{copy.deleteHint}</p>
    <div className="dialog-actions">
      <button onClick={close}>{copy.cancel}</button>
      <button className="danger" disabled={busy} onClick={onConfirm} data-testid="delete-confirm">{copy.remove}</button>
    </div>
  </div>;
}
