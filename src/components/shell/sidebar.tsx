import { GearIcon } from "@phosphor-icons/react/dist/csr/Gear";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { PlusCircleIcon } from "@phosphor-icons/react/dist/csr/PlusCircle";
import { TrayIcon } from "@phosphor-icons/react/dist/csr/Tray";
import { SparkleIcon } from "@phosphor-icons/react/dist/csr/Sparkle";
import { AlarmIcon } from "@phosphor-icons/react/dist/csr/Alarm";
import type { Dictionary } from "../../i18n";
import type { Session } from "../../lib/use-session";

export function Sidebar({ t, session, settings, reset, openSettings, openTask }: {t: Dictionary; session: Session; settings: boolean; reset(): void; openSettings(): void; openTask(id: string): void}) {
  return <aside className="sidebar" aria-label="CodeHarness">
    <div className="brand"><span className="brand-mark" /><span dir="ltr">CodeHarness</span></div>
    <nav><button className={`nav-item ${!settings ? "active" : ""}`} onClick={reset} disabled={session.busy}><PlusCircleIcon size={18} /><span>{t.newTask}</span></button>
      <a className="nav-item" href="/approvals/"><TrayIcon size={18} /><span>{t.approvals}</span></a>
      <button className="nav-item" disabled title={t.soon}><SparkleIcon size={18} /><span>{t.customize}</span></button>
      <button className="nav-item" disabled title={t.soon}><AlarmIcon size={18} /><span>{t.schedule}</span></button>
    </nav>
    <div className="workspace-label">{t.workspaces} ({new Intl.NumberFormat(session.locale).format(session.spaces.recent?.length ?? 0)})</div>
    <div className="workspace-history">{session.spaces.recent?.map(workspace => <details key={workspace.path} open={session.workspace === workspace.path}>
      <summary><FolderIcon size={18} /><span dir="auto">{workspace.name}</span></summary>
      <button className="workspace-select-action" disabled={session.busy} onClick={() => void session.selectWorkspace(workspace.path)}>{t.workspaceSelect}</button>
      <a className="workspace-select-action" href={`/workspaces/?path=${encodeURIComponent(workspace.path)}`}>{t.openWorkspace}</a>
      {!session.spaces.tasks?.some(task => task.workspace === workspace.path) && <p className="muted">{t.noTasks}</p>}
      {session.spaces.tasks?.filter(task => task.workspace === workspace.path).map(task => <button key={task.id} className="task-link" disabled={session.busy} onClick={() => openTask(task.id)}><span className={`task-dot ${task.status}`} /><span dir="auto">{task.title}</span><span className="sr-only">{task.status}</span></button>)}
    </details>)}</div>
    <button className={`nav-item settings ${settings ? "active" : ""}`} onClick={openSettings} disabled={session.busy}><GearIcon size={18} /><span>{t.settings}</span></button>
  </aside>;
}
