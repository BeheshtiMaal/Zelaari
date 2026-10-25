"use client";
import type { Dictionary } from "../../i18n";
import type { ProviderRecord } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { ProbeStatus } from "./probe-status";
import { Hint } from "../hint";

/** The model cards. Adding and editing both open the same dialog, owned by the settings screen. */
export function ModelsSection({ session, t, edit }: { session: Session; t: Dictionary; edit(provider: ProviderRecord | null): void }) {
  const number = (n: number) => new Intl.NumberFormat(session.locale).format(n);
  return <>
    {!session.vaultOk && <p className="error" role="alert">{t.probeDetails.vault}</p>}
    {session.models.map(provider => <article className={`model-card ${session.settings.default_model === provider.id ? "is-default" : ""}`} key={provider.id} data-testid="model-card">
      <div className="card-heading"><strong>{provider.kind === "demo" ? `${t.demo} (${t.offline})` : provider.name}</strong>{session.settings.default_model === provider.id && <span className="default-chip">{t.defaultModel}</span>}<div className="card-actions"><button disabled={!!session.testing} onClick={() => void session.testModel(provider.id ?? "demo")}>{t.test}</button>{provider.kind !== "demo" ? <button onClick={() => edit(provider)}>{t.edit}</button> : <Hint text={t.demoOffline}><button disabled>{t.edit}</button></Hint>}</div></div>
      <p className="provider-url" dir="ltr">{provider.base_url ? `${provider.base_url} · ` : ""}{provider.model}</p>
      <p className="muted">{t.contextDetected}: {provider.kind === "demo" ? "—" : `${provider.context?.estimated ? "~" : ""}${number(provider.context?.tokens ?? 32768)}`} · {provider.kind === "demo" ? t.demoOffline : <>{t.keyStored} <bdi dir="ltr">••••{provider.key_suffix}</bdi></>}</p>
      <ProbeStatus provider={provider} t={t} edit={provider.kind === "demo" ? undefined : () => edit(provider)} test={() => void session.testModel(provider.id ?? "demo")} choose={() => edit(null)} />
      {session.settings.default_model !== provider.id && <button className="text-button" disabled={!provider.supports_tools || provider.probe?.status !== "ok"} onClick={() => void session.makeDefault(provider.id ?? "demo")}>{t.makeDefault}</button>}
    </article>)}
  </>;
}
