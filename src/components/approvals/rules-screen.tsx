"use client";
import { approvalCopy } from "../../i18n/approvals";
import type { Session } from "../../lib/use-session";
import { useRules } from "../../lib/use-rules";
import type { Rule } from "../../lib/protocol";
import { recordKey } from "../../lib/inbox";

export function RulesScreen({ session }: { session: Session }) {
  const t = approvalCopy(session.locale), editor = useRules(session.workspace);
  return <div className="rules-screen">
    <header><h1>{t.customize}</h1><p className="muted">{t.customizeHelp}</p></header>
    <div className="inbox-tabs customize-tabs" aria-label={t.customize}>
      {[t.skills, t.agents, t.rules, t.memory, t.connectors].map(label => <button key={label} disabled={label !== t.rules} aria-pressed={label === t.rules}>{label}</button>)}
    </div>
    <label className="rules-workspace">{t.workspace}<select value={session.workspace} onChange={event => void session.selectWorkspace(event.target.value)}>{session.spaces.recent?.map(workspace => <option key={workspace.path} value={workspace.path}>{workspace.name}</option>)}</select></label>
    {!session.workspace ? <p className="muted">{t.chooseWorkspace}</p> : <>
      <section className="rules-panel"><h2>{t.rules}</h2>
        <label className="rules-mode">{t.mode}<select value={editor.mode} disabled={editor.busy} onChange={event => editor.setMode(event.target.value as "ask" | "auto" | "read-only")}><option value="ask">Ask</option><option value="auto">Auto</option><option value="read-only">Read-only</option></select></label>
        <p className="muted">{t.rulePolicy}</p>
        <div className="rules-table"><table><thead><tr><th>{t.tool}</th><th>{t.glob}</th><th>{t.action}</th><th><span className="sr-only">{t.remove}</span></th></tr></thead><tbody>
          {editor.rows.map((row, index) => <tr key={index}><td><input dir="ltr" aria-label={`${t.tool} ${index + 1}`} value={row.tool} disabled={editor.busy} onChange={event => editor.update(index, { tool: event.target.value })} /></td><td><input dir="ltr" aria-label={`${t.glob} ${index + 1}`} value={row.glob} disabled={editor.busy} onChange={event => editor.update(index, { glob: event.target.value })} /></td><td><select aria-label={`${t.action} ${index + 1}`} value={row.action} disabled={editor.busy} onChange={event => editor.update(index, { action: event.target.value as Rule["action"] })}><option value="allow">{t.allowAction}</option><option value="ask">{t.askAction}</option><option value="deny">{t.denyAction}</option></select></td><td><button disabled={editor.busy} onClick={() => editor.setRows(editor.rows.filter((_, at) => at !== index))}>{t.remove}</button></td></tr>)}
        </tbody></table></div>
        <div className="approval-actions"><button disabled={editor.busy} onClick={() => editor.setRows([...editor.rows, { tool: "edit_file", glob: "src/**", action: "ask" }])}>{t.add}</button><button className="approve" disabled={editor.busy || !!editor.proposal} onClick={() => void editor.save()}>{t.save}</button><button disabled={editor.busy} onClick={() => void editor.load()}>{t.refresh}</button></div>
        {editor.error && <p className="error" role="alert">{t.error}</p>}
        {editor.proposal && <p role="status" className="warning">{t.staged} <a href={`/approvals/?approval=${encodeURIComponent(recordKey(editor.proposal.request))}`}>{t.open}</a></p>}
      </section>
      {editor.effective && <section className="rules-panel"><h2>{t.defaults}</h2><dl className="rules-defaults">{Object.entries(editor.effective.defaults ?? {}).map(([category, action]) => <div key={category}><dt>{category}</dt><dd>{action === "allow" ? t.allowAction : action === "ask" ? t.askAction : t.denyAction}</dd></div>)}</dl><p className="muted">{t.rulePolicy}</p></section>}
    </>}
  </div>;
}
