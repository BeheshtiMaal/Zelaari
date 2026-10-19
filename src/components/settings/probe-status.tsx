import type { Dictionary } from "../../i18n";
import type { ProviderRecord } from "../../lib/protocol";

export function ProbeStatus({ provider, t, edit, test, choose }: {
  provider: ProviderRecord; t: Dictionary; edit?: () => void; test?: () => void; choose?: () => void;
}) {
  const probe = provider.probe;
  if (provider.kind === "demo") return <p className="success">{t.available}</p>;
  if (probe?.status === "ok") return <p className="success">{t.testOk}</p>;
  if (probe?.status === "testing") return <p role="status">{t.testing}</p>;
  if (probe?.status === "retrying") return <p className="warning" role="status">{t.probeErrors.rate_limit} · {t.retrying} {new Intl.NumberFormat(document.documentElement.lang).format(probe.retry_seconds ?? 0)} {t.seconds}</p>;
  if (!probe?.code) return <p className="muted">{t.untested}</p>;
  const code = probe.code;
  return <div className={`provider-error ${code === "no_tools" || code === "rate_limit" ? "amber" : ""}`} role="alert">
    <strong>{t.probeErrors[code]}</strong><p>{t.probeDetails[code]}</p>
    {code === "rate_limit" && <span>{t.attemptsEnded}</span>}
    <div className="button-row">
      {edit && <button type="button" onClick={edit}>{t.editKey}</button>}
      {test && <button type="button" onClick={test}>{t.retry}</button>}
      {choose && <button type="button" onClick={choose}>{t.otherModel}</button>}
    </div>
  </div>;
}
