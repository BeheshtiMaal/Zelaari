"use client";
import { useEffect, useState } from "react";
import type { Session } from "../../lib/use-session";
import { customizeCopy } from "../../i18n/customize";
import { RulesScreen } from "../approvals/rules-screen";
import { SkillsTab } from "./skills-tab";
import { ConnectorsTab } from "./connectors-tab";
import { AgentsTab } from "./agents-tab";
import { MemoryTab } from "./memory-tab";
import { useOverview } from "../../lib/use-customize";
import { localeDigits } from "../../lib/localised-number";

export type CustomizeTab = "skills" | "agents" | "rules" | "memory" | "connectors";
const TABS: CustomizeTab[] = ["skills", "agents", "rules", "memory", "connectors"];

export function CustomizeScreen({ session, initial = "skills" }: { session: Session; initial?: CustomizeTab }) {
  const [tab, setTab] = useState<CustomizeTab>(initial);
  // Settings links here with `?tab=rules`; read it after mount so the static export still renders.
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("tab") as CustomizeTab | null;
    if (requested && TABS.includes(requested)) setTab(requested);
  }, []);
  const copy = customizeCopy(session.locale);
  const { counts } = useOverview(session.workspace);
  return <div className="customize-screen">
    <header className="customize-heading">
      <div><h1>{copy.title}</h1><p className="muted">{copy.subtitle}</p></div>
      {counts && <p className="customize-counts muted" data-testid="customize-counts">
        {localeDigits(counts.skills ?? 0, session.locale)} {copy.counts} ·{" "}
        {localeDigits(counts.enabled_skills ?? 0, session.locale)} {copy.enabled} ·{" "}
        {localeDigits(counts.servers ?? 0, session.locale)} {copy.servers}
      </p>}
    </header>
    <div className="inbox-tabs customize-tabs" role="tablist" aria-label={copy.title}>
      {TABS.map(item => <button key={item} role="tab" aria-selected={tab === item}
        data-testid={`customize-tab-${item}`} onClick={() => setTab(item)}>
        {copy.tabs[item]}
      </button>)}
    </div>
    <div className="customize-body">
      {tab === "skills" ? <SkillsTab session={session} copy={copy} />
        : tab === "agents" ? <AgentsTab session={session} copy={copy} />
          : tab === "rules" ? <RulesScreen session={session} bare />
            : tab === "memory" ? <MemoryTab session={session} copy={copy} />
              : <ConnectorsTab session={session} copy={copy} />}
    </div>
  </div>;
}
