"use client";
import { useEffect, useRef, useState } from "react";
import { dictionary, type Locale } from "../i18n";
import type { RunRequest } from "../lib/protocol";
import { useSession } from "../lib/use-session";
import { useRun } from "../store/run";
import { Message } from "../genui/message";
import { Sidebar } from "./shell/sidebar";
import { Composer } from "./composer";

export function TaskScreen() {
  const [locale, setLocale] = useState<Locale>("fa");
  const [task, setTask] = useState("");
  const [model, setModel] = useState<RunRequest["model"]>("demo");
  const session = useSession();
  const run = useRun();
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const language = new URLSearchParams(window.location.search).get("lang") === "en" ? "en" : "fa";
    setLocale(language); document.documentElement.lang = language;
    document.documentElement.dir = language === "fa" ? "rtl" : "ltr";
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [run.seq]);
  const t = dictionary(locale);
  const running = run.runId !== null;
  const submit = () => { if (task.trim() && !session.busy) void session.start(task.trim(), model); };
  return <div className="app-shell" data-ready={session.ready}>
    <Sidebar t={t} disabled={session.busy} reset={() => { run.reset(); setTask(""); }} />
    <main className={`surface ${running ? "run-surface" : "home-surface"}`}>
      {running && <header className="run-header"><h1>{run.task}</h1><div className="run-actions">
        <span role="status">{run.status === "completed" ? t.completed : run.status === "stopped" ? t.stopped : run.status === "error" ? t.error : t.reading}</span>
        <button className="stop" disabled={!session.busy} onClick={() => void session.stop()}>{t.stop}</button>
      </div></header>}
      {running ? <div className="timeline" aria-live="polite"><div className="chat-column">
        <div className="user-message" dir="auto">{run.task}</div>
        {run.items.map((item, index) => item.kind === "message" ?
          <Message key={item.id} text={item.text} streaming={session.busy && index === run.items.length - 1} /> :
          <details className="tool-line" key={item.id} data-testid="tool-line"><summary><span className="status-dot" />{t.reading} <code>{String(item.args.file_path ?? item.name)}</code></summary><pre className="readable" dir="auto">{item.result ?? "…"}</pre></details>)}
        <div ref={end} />
      </div></div> : <h1 className="home-title">{t.title}</h1>}
      <div className="compose-region"><div className="chat-column">
        {!running && <div className="hints">{t.hints.map(hint => <button key={hint} disabled title={t.soon}>{hint}</button>)}</div>}
        <Composer t={t} task={task} setTask={setTask} ready={session.ready} busy={session.busy} workspace={session.workspace}
          model={model} setModel={setModel} pickWorkspace={() => void session.pickWorkspace()} submit={submit} />
        {session.failed || run.error ? <p className="error" role="alert">{session.ready ? t.error : t.offline}</p> :
          <p className="footnote" role="status">{!session.ready ? t.starting : running ? t.footer : t.ready}</p>}
      </div></div>
    </main>
  </div>;
}
