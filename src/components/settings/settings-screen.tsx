import { useState } from "react";
import { PlusIcon } from "@phosphor-icons/react/dist/csr/Plus";
import type { Dictionary } from "../../i18n";
import { settingsCopy } from "../../i18n/settings";
import type { ProviderRecord } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { AboutSection } from "./about-section";
import { AppearanceSection } from "./appearance-section";
import { ContextSettingsForm } from "./context-settings";
import { DataSection } from "./data-section";
import { ModelDialog } from "./model-dialog";
import { ModelsSection } from "./models-section";
import { PermissionsSection } from "./permissions-section";
import { SettingsFrame } from "./settings-frame";
import { TerminalSettingsForm } from "./terminal-settings";

export function SettingsScreen({ session, t, addInitially = false }: { session: Session; t: Dictionary; addInitially?: boolean }) {
  const [section, setSection] = useState(0);
  const [dialog, setDialog] = useState(addInitially), [existing, setExisting] = useState<ProviderRecord | null>(null);
  const edit = (provider: ProviderRecord | null) => { setExisting(provider); setDialog(true); };
  const copy = settingsCopy(session.locale), intro = copy.intro;
  return <div className="settings-layout">
    <nav className="settings-nav" aria-label={t.settings}><h1>{t.settings}</h1>{t.sections.map((label, i) => <button key={label} className={section === i ? "active" : ""} aria-current={section === i ? "page" : undefined} onClick={() => setSection(i)}>{label}</button>)}</nav>
    {section === 0 && <SettingsFrame title={t.sections[0]} intro={intro.models} action={<button className="light-button" disabled={!session.ready} onClick={() => edit(null)}><PlusIcon size={16} />{t.addModel}</button>}>
      <ModelsSection session={session} t={t} edit={edit} />
    </SettingsFrame>}
    {section === 1 && <SettingsFrame title={t.sections[1]} intro={intro.appearance}><AppearanceSection session={session} /></SettingsFrame>}
    {section === 2 && <SettingsFrame title={t.sections[2]} intro={intro.permissions}><PermissionsSection session={session} /></SettingsFrame>}
    {section === 3 && <SettingsFrame title={t.sections[3]} intro={intro.context}><ContextSettingsForm session={session} /></SettingsFrame>}
    {section === 4 && <SettingsFrame title={t.sections[4]} intro={intro.terminal}><TerminalSettingsForm session={session} /></SettingsFrame>}
    {section === 5 && <SettingsFrame title={t.sections[5]} intro={intro.data}><DataSection session={session} /></SettingsFrame>}
    {section === 6 && <SettingsFrame title={t.sections[6]} intro={intro.about}><AboutSection session={session} /></SettingsFrame>}
    {dialog && <ModelDialog session={session} existing={existing} t={t} close={() => setDialog(false)} />}
  </div>;
}
