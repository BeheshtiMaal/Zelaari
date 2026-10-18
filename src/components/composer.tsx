import { ArrowUpIcon, CaretDownIcon, FolderIcon, GitBranchIcon, PlusIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import * as Tooltip from "@radix-ui/react-tooltip";
import type { Dictionary } from "../i18n";
import type { RunRequest } from "../lib/protocol";

interface Props {
  t: Dictionary; task: string; setTask(task: string): void;
  ready: boolean; busy: boolean; workspace: string;
  model: RunRequest["model"]; setModel(model: RunRequest["model"]): void;
  pickWorkspace(): void; submit(): void;
}
export function Composer({ t, task, setTask, ready, busy, workspace, model, setModel, pickWorkspace, submit }: Props) {
  return <form className="composer-frame" onSubmit={event => { event.preventDefault(); submit(); }}>
    <div className="composer">
      <label className="sr-only" htmlFor="task">{t.taskLabel}</label>
      <textarea id="task" rows={2} placeholder={t.placeholder} value={task} disabled={!ready || busy}
        onChange={event => setTask(event.target.value)} onKeyDown={event => {
          if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); }
        }} />
      <div className="composer-toolbar">
        <button type="button" className="icon-button" disabled aria-label={t.add}><PlusIcon size={22} /></button>
        <div className="model-send">
          <Tooltip.Provider><Tooltip.Root><Tooltip.Trigger asChild>
            <button className="context-ring" type="button" aria-label={t.soon}><svg viewBox="0 0 36 36" width="22" height="22" aria-hidden="true"><circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" strokeWidth="4" /></svg></button>
          </Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="tooltip" sideOffset={10}>{t.soon}</Tooltip.Content></Tooltip.Portal></Tooltip.Root></Tooltip.Provider>
          <label className="model-select"><span className="sr-only">Model</span><select value={model} disabled={busy} onChange={event => setModel(event.target.value as RunRequest["model"])}>
            <option value="demo">{t.demo}</option><option value="openai-compatible">{t.real}</option>
          </select><CaretDownIcon size={14} /></label>
          <button className="send" type="submit" disabled={!ready || busy || !task.trim() || !workspace} aria-label={t.send}><ArrowUpIcon size={20} /></button>
        </div>
      </div>
    </div>
    <div className="workspace-toolbar">
      <button type="button" onClick={pickWorkspace} disabled={!ready || busy} className="toolbar-button" data-testid="pick-workspace"><FolderIcon size={16} /><span dir="auto">{workspace ? workspace.split(/[\\/]/).pop() : t.workspace}</span><CaretDownIcon size={14} /></button>
      <button type="button" className="toolbar-button" disabled title={t.soon}><GitBranchIcon size={16} /><span dir="ltr">—</span></button>
      <label className="worktree"><input type="checkbox" disabled />Worktree</label>
      <button type="button" className="toolbar-button" disabled title={t.soon}><ShieldCheckIcon size={16} />{t.mode}<CaretDownIcon size={14} /></button>
    </div>
  </form>;
}
