"use client";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import { useEffect, useRef, useState } from "react";
import type { Locale } from "../../i18n";
import { fill, terminalCopy } from "../../i18n/terminal";
import { commandResult, killNote, visibleOutput } from "../../lib/terminal";

const THEME = { background: "#0B1118", foreground: "#D6E0EA", cursor: "#0B1118", selectionBackground: "#1F2933" };

/** Read-only command output. It never takes input and never renders HTML. */
export function TerminalPanel({ command, result, limit = 200, locale }: {
  command: string;
  result: string | null;
  limit?: number;
  locale: Locale;
}) {
  const t = terminalCopy(locale), host = useRef<HTMLDivElement>(null), term = useRef<Terminal | null>(null);
  const [expanded, setExpanded] = useState(false);
  const parsed = result ? commandResult(result) : null;
  const shown = parsed ? visibleOutput(parsed, expanded ? Number.MAX_SAFE_INTEGER : limit) : null;
  const body = parsed
    ? shown!.text + (parsed.timedOut ? killNote(parsed.timeoutSeconds, t) : "")
    : result ?? "";
  useEffect(() => {
    if (!host.current) return;
    const instance = new Terminal({
      convertEol: true, disableStdin: true, cursorBlink: false, fontSize: 12.5, fontFamily: "Consolas, monospace",
      theme: THEME, scrollback: 2000, allowTransparency: true,
    });
    const fit = new FitAddon();
    instance.loadAddon(fit);
    instance.open(host.current);
    // Output only: xterm ships a helper textarea for keyboard input, and a read-only
    // panel must not offer a way to type into it.
    host.current.querySelector("textarea")?.remove();
    fit.fit();
    term.current = instance;
    const observer = new ResizeObserver(() => { try { fit.fit(); } catch { /* host is hidden */ } });
    observer.observe(host.current);
    return () => { observer.disconnect(); instance.dispose(); term.current = null; };
  }, []);
  useEffect(() => {
    const instance = term.current;
    if (!instance) return;
    instance.reset();
    if (body) instance.write(body.replace(/\n/g, "\r\n"));
    else if (!parsed) instance.write("");
  }, [body, parsed]);
  const exit = parsed?.exitCode;
  const rows = Math.max(1, body ? body.split("\n").length : 1);
  return <section className={`terminal-panel ${parsed?.timedOut ? "terminal-timeout" : ""}`} data-testid="terminal-panel" dir="ltr" aria-label={t.terminal}>
    <header className="terminal-header">
      <code className="terminal-command">$ {command}</code>
      <span className="terminal-status">
        {parsed?.timedOut ? <span className="terminal-tag">{t.timeoutTag}</span>
          : exit === null || exit === undefined ? t.running
          : <>{t.exit} <b data-testid="terminal-exit">{exit}</b></>}
      </span>
    </header>
    {parsed?.timedOut && <p className="terminal-timeout-note">{fill(t.timeout, parsed.timeoutSeconds, locale)}</p>}
    <div className="terminal-body" ref={host} aria-readonly="true" style={{ blockSize: `${Math.min(420, Math.max(64, rows * 19 + 16))}px` }} />
    {shown && shown.hidden > 0 && <button type="button" className="terminal-more" data-testid="terminal-more" onClick={() => setExpanded(true)}>{t.showMore} · {shown.hidden} {t.hidden}</button>}
  </section>;
}
