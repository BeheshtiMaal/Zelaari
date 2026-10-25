import { ArrowUpIcon } from "@phosphor-icons/react/dist/csr/ArrowUp";
import { FolderIcon } from "@phosphor-icons/react/dist/csr/Folder";
import { GitBranchIcon } from "@phosphor-icons/react/dist/csr/GitBranch";
import { PlusIcon } from "@phosphor-icons/react/dist/csr/Plus";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import type { Dictionary } from "../i18n";
import type { Session } from "../lib/use-session";
import { Hint } from "./hint";
import { useCommands, useCommandList } from "../lib/use-commands";
import { questionCopy } from "../i18n/questions";
import { customizeCopy } from "../i18n/customize";
import { contextCopy } from "../i18n/context";
import { useRun } from "../store/run";
import { currentContext } from "../lib/timeline";
import { useVerifySettings } from "../lib/use-verify-settings";
import { useRunSummary } from "../lib/use-summary";
import { ContextRing } from "./context/context-ring";
import { resolve } from "../lib/shortcuts";
export function Composer({ t, task, setTask, session: s, submit }: {t: Dictionary; task: string; setTask(task: string): void; session: Session; submit(): void}) {
  const commandList = useCommandList(s.workspace);
  const commands = useCommands(task, setTask, commandList), q = questionCopy(s.locale), c = contextCopy(s.locale);
  const events = useRun(state => state.events), runId = useRun(state => state.runId);
  const settings = useVerifySettings(s.workspace);
  const summarised = events.filter(event => event.type === "context.summarized").length;
  const summary = useRunSummary(runId, summarised);
  const context = currentContext(events);
  const ring = settings.value?.context ?? {};
  return <form className="composer-frame" onSubmit={event => { event.preventDefault(); submit(); }}>
    <div className="composer">
      <label className="sr-only" htmlFor="task">{t.taskLabel}</label>
      {commands.matches.length > 0 && <div className="command-picker" role="listbox" id="composer-commands" aria-label={q.options}>{commands.matches.map((command, at) => <button key={command.name} type="button" role="option" aria-selected={at === commands.index} id={`command-${command.name}`} onMouseDown={event => event.preventDefault()} onClick={() => commands.choose(command.command)}><code dir="ltr">{command.command}</code><span>{command.description}</span>{command.requires_approval && <span className="type-chip">{customizeCopy(s.locale).needsApproval}</span>}</button>)}</div>}
      <textarea id="task" rows={2} role="combobox" aria-autocomplete="list" aria-expanded={commands.matches.length > 0} aria-controls="composer-commands" aria-activedescendant={commands.matches.length ? `command-${commands.matches[commands.index].name}` : undefined} placeholder={t.placeholder} value={task} disabled={!s.ready} onChange={event => setTask(event.target.value)} onKeyDown={event => {
        if (commands.keyDown(event) || event.nativeEvent.isComposing) return;
        // The picker has first refusal above; what is left is the table's business.
        const hit = resolve("composer", { key: event.key, shiftKey: event.shiftKey, ctrlKey: event.ctrlKey, metaKey: event.metaKey, altKey: event.altKey, tag: "TEXTAREA" });
        if (hit?.action === "send") { event.preventDefault(); submit(); }
      }} />
      {commands.active && <p className="active-skill" data-testid="active-skill" dir="auto"><code dir="ltr">{commands.active.command}</code><span>{commands.active.name}</span></p>}
      <div className="composer-toolbar"><Hint text={t.soon}><button type="button" className="icon-button" disabled aria-label={t.add}><PlusIcon size={22} /></button></Hint>
        <div className="model-send">{context?.type === "context.updated" && (ring.show_ring ?? true) && <ContextRing event={context} locale={s.locale} threshold={ring.compaction_percent ?? 60} summary={!!summary} busy={s.busy} onNewChat={() => void s.start(task.trim() || c.continueTask, false, runId ?? undefined)} />}
          <label className="model-select"><span className="sr-only">{t.modelSelect}</span><select aria-label={t.modelSelect} value={s.model} disabled={s.busy} onChange={event => s.setModel(event.target.value)}><option value="">{t.modelSelect}</option>{s.models.map(model => <option key={model.id} value={model.id} disabled={!model.supports_tools || model.probe?.status !== "ok"}>{model.kind === "demo" ? t.demo : model.name}</option>)}</select></label>
          <button className="send" type={s.busy ? "button" : "submit"} onClick={s.busy ? () => void s.stop() : undefined} disabled={!s.ready || (!s.busy && (!task.trim() || !s.workspace || !s.usableModel))} aria-label={s.busy ? t.stop : t.send}>{s.busy ? <span aria-hidden="true">■</span> : <ArrowUpIcon size={20} />}</button>
        </div>
      </div>
    </div>
    <div className="workspace-toolbar">
      <div className="workspace-picker"><FolderIcon size={16} /><select aria-label={t.workspaceSelect} value={s.workspace} disabled={!s.ready} onChange={event => { if (event.target.value === "__pick") void s.pickWorkspace(); else void s.selectWorkspace(event.target.value); }}><option value="">{t.workspaceSelect}</option>{s.spaces.recent?.map(workspace => <option key={workspace.path} value={workspace.path}>{workspace.name}</option>)}<option value="__pick">{t.workspace}…</option></select><button type="button" className="toolbar-button" onClick={() => void s.pickWorkspace()} disabled={!s.ready || s.busy} data-testid="pick-workspace" aria-label={t.workspace}>…</button></div>
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
