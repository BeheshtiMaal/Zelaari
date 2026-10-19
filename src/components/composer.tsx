import { ArrowUpIcon } from "@phosphor-icons/react/dist/csr/ArrowUp";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { GitBranchIcon } from "@phosphor-icons/react/dist/csr/GitBranch";
import { PlusIcon } from "@phosphor-icons/react/dist/csr/Plus";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import type { Dictionary } from "../i18n";
import type { Session } from "../lib/use-session";
import { Hint } from "./hint";
export function Composer({ t, task, setTask, session: s, submit }: {t: Dictionary; task: string; setTask(task: string): void; session: Session; submit(): void}) {
  return <form className="composer-frame" onSubmit={event => { event.preventDefault(); submit(); }}>
    <div className="composer">
      <label className="sr-only" htmlFor="task">{t.taskLabel}</label>
      <textarea id="task" rows={2} placeholder={t.placeholder} value={task} disabled={!s.ready || s.busy} onChange={event => setTask(event.target.value)} onKeyDown={event => {
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); }
      }} />
      <div className="composer-toolbar"><Hint text={t.soon}><button type="button" className="icon-button" disabled aria-label={t.add}><PlusIcon size={22} /></button></Hint>
        <div className="model-send"><Hint text={t.placeholderRing}><span className="context-ring"><svg viewBox="0 0 36 36" width="22" height="22" aria-hidden="true"><circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" strokeWidth="4" /></svg></span></Hint>
          <label className="model-select"><span className="sr-only">{t.modelSelect}</span><select aria-label={t.modelSelect} value={s.model} disabled={s.busy} onChange={event => s.setModel(event.target.value)}><option value="">{t.modelSelect}</option>{s.models.map(model => <option key={model.id} value={model.id} disabled={!model.supports_tools || model.probe?.status !== "ok"}>{model.kind === "demo" ? t.demo : model.name}</option>)}</select></label>
          <button className="send" type="submit" disabled={!s.ready || s.busy || !task.trim() || !s.workspace || !s.usableModel} aria-label={t.send}><ArrowUpIcon size={20} /></button>
        </div>
      </div>
    </div>
    <div className="workspace-toolbar">
      <div className="workspace-picker"><FolderIcon size={16} /><select aria-label={t.workspaceSelect} value={s.workspace} disabled={!s.ready || s.busy} onChange={event => { if (event.target.value === "__pick") void s.pickWorkspace(); else void s.selectWorkspace(event.target.value); }}><option value="">{t.workspaceSelect}</option>{s.spaces.recent?.map(workspace => <option key={workspace.path} value={workspace.path}>{workspace.name}</option>)}<option value="__pick">{t.workspace}…</option></select><button type="button" className="toolbar-button" onClick={() => void s.pickWorkspace()} disabled={!s.ready || s.busy} data-testid="pick-workspace" aria-label={t.workspace}>…</button></div>
      {s.branches.git && (s.branches.branches ?? []).length > 0 ?
        <label className="toolbar-button branch-chip" data-testid="branch"><GitBranchIcon size={16} /><span className="sr-only">{t.branch}</span>
          <select aria-label={t.branch} value={s.branch ?? ""} disabled={s.busy} onChange={event => void s.switchBranch(event.target.value)}>
            {(s.branches.branches ?? []).map(name => <option key={name} value={name}>{name}</option>)}
          </select>
        </label> :
        s.branch ? <span className="toolbar-button" data-testid="branch"><GitBranchIcon size={16} /><span dir="ltr">{s.branch}</span></span> : null}
      <Hint text={s.branches.git ? t.worktreeHelp : t.worktreeUnavailable}><label className="worktree"><input type="checkbox" data-testid="worktree" checked={s.worktree} disabled={s.busy || !s.branches.git} onChange={event => s.setWorktree(event.target.checked)} />{t.worktree}</label></Hint>
      <label className="toolbar-button"><ShieldCheckIcon size={16} /><span className="sr-only">{t.mode}</span><select aria-label={t.mode} disabled={s.busy} value={s.mode} onChange={e => s.setMode(e.target.value as "ask" | "auto" | "read-only")}><option value="ask">{t.mode}</option><option value="read-only">{t.readOnly}</option><option value="auto">{t.auto}</option></select></label>
    </div>
  </form>;
}
