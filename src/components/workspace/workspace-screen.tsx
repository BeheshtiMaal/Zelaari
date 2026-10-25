"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpIcon } from "@phosphor-icons/react/dist/csr/ArrowUp";
import { FileIcon } from "@phosphor-icons/react/dist/csr/File";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import type { Dictionary } from "../../i18n";
import { statesCopy } from "../../i18n/states";
import { api } from "../../lib/api";
import { useUndo } from "../../lib/use-undo";
import { changedLineSet, entriesOf, fileOf, parentPath, workspaceSubtitle } from "../../lib/files";
import type { FileEntry, FileListing } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { Sidebar } from "../shell/sidebar";
import { CrashCard } from "../states/crash-card";
import { EmptyState } from "../states/empty-state";
import { connection } from "../../lib/desktop";
import { useEngine } from "../../lib/use-engine";

export function WorkspaceScreen({ t, session, root }: { t: Dictionary; session: Session; root: string }) {
  const states = statesCopy(session.locale);
  const [folder, setFolder] = useState("");
  const [system, setSystem] = useState(false);
  const [listing, setListing] = useState<FileListing | null>(null);
  const [selected, setSelected] = useState<FileListing | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => { if (root && root !== session.workspace) void session.selectWorkspace(root); }, [root, session]);
  const active = root || session.workspace;

  const load = useCallback(async (path: string, showSystem: boolean) => {
    if (!active) return;
    try {
      setListing(await api<FileListing>(`/files?workspace=${encodeURIComponent(active)}&path=${encodeURIComponent(path)}&system=${showSystem}`));
      setFailed(false);
    } catch { setFailed(true); }
  }, [active]);

  useEffect(() => { setSelected(null); void load(folder, system); }, [folder, system, load]);

  const open = useCallback(async (entry: FileEntry) => {
    if (entry.kind === "dir") { setFolder(entry.path); return; }
    try { setSelected(await api<FileListing>(`/files?workspace=${encodeURIComponent(active)}&path=${encodeURIComponent(entry.path)}&system=${system}`)); setFailed(false); }
    catch { setFailed(true); }
  }, [active, system]);

  const entries = useMemo(() => entriesOf(listing), [listing]);
  const file = fileOf(selected);
  const undo = useUndo(active, file?.path);
  async function revert() {
    const result = await undo.revert();
    if (!result || !file) return;
    if (result.existed) await open({ name: file.path, path: file.path, kind: "file", size: 0 });
    else setSelected(null);
    await load(folder, system);
  }
  const highlighted = useMemo(() => changedLineSet(file?.changed_lines), [file]);
  const tasks = useMemo(() => session.spaces.tasks?.filter(task => task.workspace === active) ?? [], [session.spaces.tasks, active]);
  const name = active ? active.split(/[\\/]/).filter(Boolean).pop() ?? active : "";
  const rows = file ? file.text.split("\n") : [];
  // The workspace page has its own shell, so it carries its own crash card.
  const engine = useEngine(id => void session.openTask(id));

  return <div className="app-shell" data-ready={session.ready}>
    <Sidebar t={t} session={session} settings={false} reset={() => undefined} openSettings={() => undefined} openTask={id => void session.openTask(id)} />
    <main id="main" tabIndex={-1} className="surface workspace-surface">
      <header className="ws-header">
        <div className="ws-title">
          <span className="ws-folder-icon"><FolderIcon size={30} /></span>
          <div>
            <div className="ws-name" dir="ltr">{name || t.workspaceSelect}</div>
            <div className="ws-path" dir="ltr">{workspaceSubtitle(active, session.branch)}</div>
          </div>
        </div>
        <div className="ws-actions">
          <button type="button" className="light-outline" onClick={() => void session.revealWorkspace()} disabled={!active}>{t.revealInExplorer}</button>
          <a className="light-button" href="/">{t.newTaskHere}</a>
        </div>
      </header>
      <div className="ws-grid">
        <section className="ws-files" aria-label={t.files}>
          <div className="ws-files-head">
            <b>{t.files}</b>
            <label className="ws-system"><input type="checkbox" checked={system} onChange={event => setSystem(event.target.checked)} />{t.systemFiles}</label>
          </div>
          {folder && <button type="button" className="ws-row" onClick={() => setFolder(parentPath(folder))}><span className="ws-row-icon"><ArrowUpIcon size={16} /></span><span dir="ltr">..</span></button>}
          {entries.map(entry => <button type="button" key={entry.path} className={`ws-row ${selected?.path === entry.path ? "active" : ""}`} data-depth={entry.path.split("/").length - 1} onClick={() => void open(entry)}>
            <span className="ws-row-icon">{entry.kind === "dir" ? <FolderIcon size={16} /> : <FileIcon size={16} />}</span>
            <span dir="ltr">{entry.name}</span>
            {entry.changed && <span className="ws-changed-dot" aria-label={t.changedByAgent} />}
          </button>)}
          {!entries.length && !failed && <p className="muted">{t.emptyFolder}</p>}
          {failed && <p className="error" role="alert">{t.filesUnavailable}</p>}
        </section>
        <section className="ws-viewer" aria-label={t.fileViewer}>
          <div className="ws-viewer-head">
            <span dir="ltr">{file?.path ?? t.pickFile}</span>
            {undo.available && <button type="button" className="light-outline" data-testid="undo-file" disabled={undo.busy} onClick={() => void revert()}>{t.undoChange}</button>}
            {file?.pending_approval ? <span className="ws-badge" data-testid="waiting-badge">{t.waitingApproval}</span> :
              file && highlighted.size > 0 ? <span className="ws-badge ok">{t.changedByAgent}</span> : null}
          </div>
          {undo.failed && <p className="error" role="alert">{t.undoFailed}</p>}
          {file?.binary ? <p className="muted ws-note">{t.binaryFile}</p> :
            file ? <div className="ws-code" dir="ltr">{rows.map((line, index) => <div key={index} className={`ws-line ${highlighted.has(index + 1) ? "changed" : ""}`}>
              <span className="ws-line-number">{index + 1}</span><span className="ws-line-text">{line || " "}</span>
            </div>)}{file.truncated && <p className="muted ws-note">{t.truncatedFile}</p>}</div> :
              <p className="muted ws-note">{t.pickFileHelp}</p>}
        </section>
        <section className="ws-tasks" aria-label={t.tasksHere}>
          <b>{t.tasksHere}</b>
          {tasks.map(task => <a key={task.id} className="ws-task" href={`/tasks/`} onClick={event => { event.preventDefault(); void session.openTask(task.id); }}>
            <div>{task.title}</div>
            <div className={`ws-task-status ${task.status}`}>{task.status === "completed" ? t.completed : task.status === "running" ? t.reading : task.status === "error" ? t.errorShort : t.stopped}</div>
          </a>)}
          {!tasks.length && <EmptyState testId="state-no-tasks" icon={<FileIcon size={26} />}
            label={states.noTasks.label} title={states.noTasks.title} help={states.noTasks.help}
            actions={[{ label: states.noTasks.primary, testId: "state-start-task", primary: true, onClick: () => { window.location.href = "/"; } }]} />}
          <p className="ws-task-note">{t.workspaceNote}</p>
        </section>
      </div>
    </main>
    {!engine.alive && <CrashCard locale={session.locale} restarting={engine.restarting} failed={engine.failed}
      onRestart={() => void engine.restart()} onLogs={() => void connection()?.openLogFolder()} />}
  </div>;
}
