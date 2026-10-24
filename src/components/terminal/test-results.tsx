import type { Locale } from "../../i18n";
import { terminalCopy } from "../../i18n/terminal";
import type { TestResult } from "../../lib/protocol";

/** What the verification run reported, in counts when the output stated them. */
export function TestResults({ result, locale }: { result: TestResult; locale: Locale }) {
  const t = terminalCopy(locale), number = new Intl.NumberFormat(locale);
  const counts = typeof result.passed === "number" || typeof result.failed === "number";
  return <section className="test-results" data-testid="test-results" dir="auto" aria-label={t.testResult}>
    <div className="test-chips">
      {counts ? <>
        {typeof result.passed === "number" && <span className="test-chip ok" data-testid="test-passed">{number.format(result.passed)} {t.passed}</span>}
        {typeof result.failed === "number" && result.failed > 0 && <span className="test-chip danger" data-testid="test-failed">{number.format(result.failed)} {t.failed}</span>}
      </> : <span className="test-chip neutral" data-testid="test-exit">{t.noCounts} · {t.exit} {result.exit_code === null || result.exit_code === undefined ? "—" : number.format(result.exit_code)}</span>}
      {result.status === "timeout" && <span className="test-chip danger">{t.timedOut}</span>}
      {result.status === "error" && <span className="test-chip danger">{t.errored}</span>}
    </div>
    {(result.failures?.length ?? 0) > 0 && <div className="test-failures">
      <span className="muted">{t.failures}</span>
      <ul>{result.failures!.map(name => <li key={name}><code dir="ltr">{name}</code></li>)}</ul>
    </div>}
  </section>;
}
