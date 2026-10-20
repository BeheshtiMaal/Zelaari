import { useEffect, useState } from "react";
import type { Locale } from "../../i18n";
import type { RunState } from "../../store/run";
import { duration } from "../../lib/timeline";
import { planningCopy } from "../../i18n/planning";

export function RunElapsed({ run, locale }: { run: RunState; locale: Locale }) {
  const [now, setNow] = useState(() => new Date().toISOString());
  useEffect(() => {
    if (run.status !== "running") return;
    const timer = setInterval(() => setNow(new Date().toISOString()), 1000);
    return () => clearInterval(timer);
  }, [run.status]);
  const start = run.events.find(e => e.type === "run.started");
  const end = run.events.slice().reverse().find(e => e.type === "run.finished");
  const seconds = duration(start?.ts, end?.ts ?? now);
  return seconds === null ? null : <span className="run-elapsed">{new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(seconds)} {planningCopy(locale).seconds}</span>;
}
