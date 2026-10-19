"use client";
import { useEffect, useRef, useState } from "react";
import { dictionary } from "../i18n";
import { useSession } from "../lib/use-session";
import { useRun } from "../store/run";
import { Message } from "../genui/message";
import { Sidebar } from "./shell/sidebar";
import { Composer } from "./composer";
import { SettingsScreen } from "./settings/settings-screen";
import { Hint } from "./hint";
import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { GearIcon } from "@phosphor-icons/react/dist/csr/Gear";

export function TaskScreen() {
  const [task, setTask] = useState("");
  const [view, setView] = useState<"home" | "settings" | "add-model">("home");
  const session = useSession(), run = useRun();
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [run.seq]);
  const t = dictionary(session.locale), running = run.runId !== null;
  const reset = () => { run.reset(); setTask(""); setView("home"); };
  const submit = () => { if (task.trim() && !session.busy) void session.start(task.trim()); };
  const selected = session.usableModel;
  const total = run.usage.input + run.usage.output;
  return <div className="app-shell" data-ready={session.ready}>
    <Sidebar t={t} session={session} settings={view !== "home"} reset={reset} openSettings={() => setView("settings")} openTask={id => { setView("home"); void session.openTask(id); }} />
    <main className={`surface ${view !== "home" ? "settings-surface" : running ? "run-surface" : "home-surface"}`}>
      {view !== "home" ? <SettingsScreen key={view} session={session} t={t} addInitially={view === "add-model"} /> : <>
        {running && <header className="run-header"><h1>{run.task}</h1><div className="run-actions">
          {total > 0 && <span data-testid="token-meter">{run.usage.estimated ? "~" : ""}{new Intl.NumberFormat(session.locale).format(total)} {t.tokens}</span>}
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
          {!running && <div className="hints">{t.hints.map(hint => <button key={hint} disabled={!session.ready} onClick={() => setTask(hint)}>{hint}</button>)}<Hint text={t.soon}><button className="more-hints" disabled aria-label={session.locale === "fa" ? "بیشتر" : "More"}><CaretRightIcon size={16} /></button></Hint></div>}
          <Composer t={t} task={task} setTask={setTask} session={session} submit={submit} />
          {!running && session.ready && (!session.workspace || !selected) && <div className="empty-states">
            {!session.workspace && <section className="empty-state"><div className="empty-state-label">{t.emptyWorkspaceLabel}</div><div className="empty-state-body"><span className="empty-icon"><FolderIcon size={26} /></span><strong>{t.noWorkspace}</strong><p>{t.noWorkspaceHelp}</p><button onClick={() => void session.pickWorkspace()}>{t.workspace}</button></div></section>}
            {!selected && <section className="empty-state"><div className="empty-state-label">{t.emptyModelLabel}</div><div className="empty-state-body"><span className="empty-icon"><GearIcon size={26} /></span><strong>{t.noModel}</strong><p>{t.noModelHelp}</p><div className="button-row"><button onClick={() => setView("add-model")}>{t.addModel}</button><button onClick={() => void session.makeDefault("demo")}>{t.demo}</button></div></div></section>}
          </div>}
          {session.failed || run.error || session.workspaceError ? <p className="error" role="alert">{session.workspaceError ? t.invalidWorkspace : session.ready ? t.error : t.offline}</p> :
            <p className="footnote" role="status">{!session.ready ? t.starting : running ? t.footer : t.ready}</p>}
        </div></div>
      </>}
    </main>
  </div>;
}
