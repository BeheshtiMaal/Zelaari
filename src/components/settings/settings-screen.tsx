import { useState } from "react";
import { PlusIcon } from "@phosphor-icons/react/dist/csr/Plus";
import type { Dictionary } from "../../i18n";
import type { ProviderRecord } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { ModelDialog } from "./model-dialog";
import { ProbeStatus } from "./probe-status";
import { Hint } from "../hint";

export function SettingsScreen({ session, t, addInitially = false }: {session: Session; t: Dictionary; addInitially?: boolean}) {
  const [section, setSection] = useState(0);
  const [dialog, setDialog] = useState(addInitially), [existing, setExisting] = useState<ProviderRecord | null>(null);
  const edit = (provider: ProviderRecord) => { setExisting(provider); setDialog(true); };
  const add = () => { setExisting(null); setDialog(true); };
  const number = (n: number) => new Intl.NumberFormat(session.locale).format(n);
  return <div className="settings-layout">
    <nav className="settings-nav" aria-label={t.settings}><h1>{t.settings}</h1>{t.sections.map((label, i) => <button key={label} className={section === i ? "active" : ""} aria-current={section === i ? "page" : undefined} onClick={() => setSection(i)}>{label}</button>)}</nav>
    <section className="settings-content">
      <header className="settings-heading"><div><h2>{t.sections[section]}</h2><p className="muted">{section === 0 ? t.modelsIntro : section === 1 ? t.appearanceIntro : t.soon}</p></div>{section === 0 && <button className="light-button" disabled={!session.ready} onClick={add}><PlusIcon size={16} />{t.addModel}</button>}</header>
      {!session.vaultOk && <p className="error" role="alert">{t.probeDetails.vault}</p>}
      {section === 0 && session.models.map(provider => <article className={`model-card ${session.settings.default_model === provider.id ? "is-default" : ""}`} key={provider.id}>
        <div className="card-heading"><strong>{provider.kind === "demo" ? `${t.demo} (${session.locale === "fa" ? "آفلاین" : "offline"})` : provider.name}</strong>{session.settings.default_model === provider.id && <span className="default-chip">{t.defaultModel}</span>}<div className="card-actions"><button disabled={!!session.testing} onClick={() => void session.testModel(provider.id ?? "demo")}>{t.test}</button>{provider.kind !== "demo" ? <button onClick={() => edit(provider)}>{t.edit}</button> : <Hint text={t.demoOffline}><button disabled>{t.edit}</button></Hint>}</div></div>
        <p className="provider-url" dir="ltr">{provider.base_url ? `${provider.base_url} · ` : ""}{provider.model}</p>
        <p className="muted">{t.contextDetected}: {provider.kind === "demo" ? "—" : `${provider.context?.estimated ? "~" : ""}${number(provider.context?.tokens ?? 32768)}`} · {provider.kind === "demo" ? t.demoOffline : <>{t.keyStored} <bdi dir="ltr">••••{provider.key_suffix}</bdi></>}</p>
        <ProbeStatus provider={provider} t={t} edit={provider.kind === "demo" ? undefined : () => edit(provider)} test={() => void session.testModel(provider.id ?? "demo")} choose={add} />
        {session.settings.default_model !== provider.id && <button className="text-button" disabled={!provider.supports_tools || provider.probe?.status !== "ok"} onClick={() => void session.makeDefault(provider.id ?? "demo")}>{t.makeDefault}</button>}
      </article>)}
      {section === 1 && <section className="model-card"><h3>{t.display}</h3><div className="language-row"><div><strong>{t.language}</strong><p className="muted">{t.languageDefault}</p></div><div className="language-segment" role="group" aria-label={t.language}><button aria-pressed={session.locale === "fa"} onClick={() => void session.setLocale("fa")}>فارسی</button><button aria-pressed={session.locale === "en"} onClick={() => void session.setLocale("en")}>English</button></div></div></section>}
      {section > 1 && <div className="deferred-panel">{t.soon}</div>}
    </section>
    {dialog && <ModelDialog session={session} existing={existing} t={t} close={() => setDialog(false)} />}
  </div>;
}
