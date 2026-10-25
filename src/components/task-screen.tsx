"use client";
import { RunElapsed } from "./planning/run-elapsed";
import { useEffect, useRef, useState } from "react";
import { dictionary } from "../i18n";
import { useSession } from "../lib/use-session";
import { useAppearance } from "../lib/use-appearance";
import { activityView } from "../lib/appearance";
import { useRun } from "../store/run";
import { connection } from "../lib/desktop";
import { ActivityTimeline } from "./planning/activity-timeline";
import { RunInfo } from "./planning/run-info";
import { useSteering } from "../lib/use-steering";
import { planningCopy } from "../i18n/planning";
import { Sidebar } from "./shell/sidebar";
import { Composer } from "./composer";
import { QuestionCard } from "./questions/question-card";
import { useQuestions } from "../lib/use-questions";
import { questionCopy } from "../i18n/questions";
import { InboxScreen } from "./approvals/inbox-screen";
import { ApprovalCard } from "./approvals/approval-card";
import { recordKey, useInbox } from "../lib/inbox";
import { RulesScreen } from "./approvals/rules-screen";
import { CustomizeScreen } from "./customize/customize-screen";
import { approvalCopy } from "../i18n/approvals";
import { SettingsScreen } from "./settings/settings-screen";
import { CrashCard } from "./states/crash-card";
import { EmptyState } from "./states/empty-state";
import { statesCopy } from "../i18n/states";
import { useEngine } from "../lib/use-engine";
import { Hint } from "./hint";
import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { GearIcon } from "@phosphor-icons/react/dist/csr/Gear";

export function TaskScreen({ initialView = "home" }: { initialView?: "home" | "inbox" | "rules" | "customize" }) {
  const [task, setTask] = useState("");
  const [view, setView] = useState<"home" | "settings" | "add-model" | "inbox" | "rules" | "customize">(initialView);
  const session = useSession(), run = useRun(), steering = useSteering();
  useAppearance(session.settings);
  const states = statesCopy(session.locale);
  // A restart reopens the task that was on screen, from its persisted events.
  const engine = useEngine(id => { setView("home"); void session.openTask(id); });
  const questions = useQuestions(run.runId);
  const approvals = useInbox(state => state.records);
  const decisionError = useInbox(state => state.decisionError);
  const startedRunId = useInbox(state => state.startedRunId);
  useEffect(() => {
    if (!startedRunId) return;
    useInbox.setState({ startedRunId: null });
    setView("home"); void session.openTask(startedRunId);
  }, [startedRunId]);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [run.seq]);
  const t = dictionary(session.locale), running = run.runId !== null;
  const reset = () => { session.detach(); run.reset(); setTask(""); setView("home"); };
  const submit = () => {
    if (!task.trim()) return;
    if (run.status === "running") { const draft = task; void steering.send(draft).then(sent => { if (sent) setTask(current => current === draft ? "" : current); }); }
    else { void session.start(task.trim()); setTask(""); }
  };
  const selected = session.usableModel;
  const total = run.usage.input + run.usage.output;
  const waiting = questions.filter(record => record.status === "pending").length + approvals.filter(record => record.status === "pending" && record.request.run_id === run.runId).length;
  return <div className="app-shell" data-ready={session.ready}>
    <Sidebar t={t} session={session} settings={view === "settings" || view === "add-model"} current={view === "rules" ? "customize" : view} reset={reset} openSettings={() => setView("settings")} openTask={id => { setView("home"); void session.openTask(id); }} />
    <main id="main" tabIndex={-1} className={`surface ${view !== "home" ? "settings-surface" : running ? "run-surface" : "home-surface"}`}>
      {view === "inbox" ? <InboxScreen locale={session.locale} onHome={() => setView("home")} /> : view === "customize" ? <CustomizeScreen session={session} /> : view === "rules" ? <RulesScreen session={session} /> : view !== "home" ? <SettingsScreen key={view} session={session} t={t} addInitially={view === "add-model"} /> : <>
        <div className={running ? "run-layout" : "home-layout"}><div className={running ? "run-main" : "home-main"}>
        {running && <header className="run-header"><h1>{run.task}</h1><div className="run-actions"><RunElapsed run={run} locale={session.locale} />
          {total > 0 && <span data-testid="token-meter">{run.usage.estimated ? "~" : ""}{new Intl.NumberFormat(session.locale).format(total)} {t.tokens}</span>}
          <span role="status">{run.approval ? t.paused : questions.some(record => record.status === "pending") ? questionCopy(session.locale).pending : run.status === "completed" ? t.completed : run.status === "stopped" ? t.stopped : run.status === "error" ? t.error : t.reading}</span>
          <button className="stop" disabled={!session.busy} onClick={() => void session.stop()}>{t.stop}</button>
        </div></header>}
        {running ? <div className="timeline" aria-live="polite"><div className="chat-column">
          <div className="user-message" dir="auto">{run.task}</div>
          <ActivityTimeline run={run} locale={session.locale} activity={activityView(session.settings.appearance)} retry={command => void session.retryWithLongerTimeout(command).then(() => setView("inbox"))} />
          {approvals.filter(record => record.status === "pending" && record.request.run_id === run.runId).map(record => <ApprovalCard key={recordKey(record.request)} record={record} locale={session.locale} inline />)}
          {questions.filter(record => record.status !== "pending").map(record => <QuestionCard key={record.request.call_id} record={record} locale={session.locale} />)}
          <div ref={end} />
        </div></div> : <h1 className="home-title">{t.title}</h1>}
        <div className="compose-region"><div className="chat-column">
          {questions.filter(record => record.status === "pending").map(record => <QuestionCard key={record.request.call_id} record={record} locale={session.locale} />)}
          {!running && <div className="hints">{t.hints.map((hint, index) => <button key={hint} disabled={!session.ready} onClick={() => setTask(index === 4 ? "/grill " : hint)}>{hint}</button>)}<Hint text={t.soon}><button className="more-hints" disabled aria-label={t.more}><CaretRightIcon size={16} /></button></Hint></div>}
          {Object.values(run.steering).map(message => <p className="steering-status" role="status" key={message.submission_id}><span>{planningCopy(session.locale)[message.status ?? "queued"]}</span> · {message.text}</p>)}
          {steering.error && <p className="error" role="alert">{planningCopy(session.locale).sendError}</p>}
          <Composer t={t} task={task} setTask={setTask} session={session} submit={submit} />
          {approvals.filter(record => record.status === "pending" && [session.branchApproval?.approval_id, session.worktreeApproval?.approval_id].includes(record.request.approval_id)).map(record => <ApprovalCard key={recordKey(record.request)} record={record} locale={session.locale} inline />)}
          {session.branchError && <pre className="error" role="alert" dir="ltr" data-testid="branch-error">{session.branchError}</pre>}
          {decisionError && <p className="error" role="alert" data-testid="branch-error">{decisionError === "review_failed" ? approvalCopy(session.locale).error : decisionError}</p>}
          {!running && session.ready && (!session.workspace || !selected) && <div className="empty-states">
            {!session.workspace && <EmptyState testId="state-no-workspace" icon={<FolderIcon size={26} />}
              label={states.noWorkspace.label} title={states.noWorkspace.title} help={states.noWorkspace.help}
              actions={[
                { label: states.noWorkspace.primary, testId: "state-choose-folder", primary: true, onClick: () => void session.pickWorkspace() },
                { label: states.noWorkspace.sample, testId: "state-sample-project", onClick: () => void session.openSample() },
              ]} />}
            {!selected && <EmptyState testId="state-no-model" icon={<GearIcon size={26} />}
              label={states.noModel.label} title={states.noModel.title} help={states.noModel.help}
              actions={[
                { label: states.noModel.primary, testId: "state-add-model", primary: true, onClick: () => setView("add-model") },
                { label: states.noModel.demo, testId: "state-demo-model", onClick: () => void session.makeDefault("demo") },
              ]} />}
          </div>}
          {session.failed || run.error || session.workspaceError ? <p className="error" role="alert">{session.workspaceError ? t.invalidWorkspace : session.ready ? t.error : t.offline}</p> :
            <p className="footnote" role="status">{!session.ready ? t.starting : running ? t.footer : t.ready}</p>}
        </div></div>
        </div>{running && <RunInfo run={run} locale={session.locale} waiting={waiting} />}</div>
      </>}
    </main>
    {!engine.alive && <CrashCard locale={session.locale} restarting={engine.restarting} failed={engine.failed}
      onRestart={() => void engine.restart()} onLogs={() => void connection()?.openLogFolder()} />}
  </div>;
}
