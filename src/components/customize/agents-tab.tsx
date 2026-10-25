"use client";
import { useEffect, useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import type { Session } from "../../lib/use-session";
import { EMPTY_AGENT, useAgents, type AgentDraft } from "../../lib/use-customize";

const READ_TOOLS = ["ls", "read_file", "glob", "grep"];

export function AgentsTab({ session, copy }: { session: Session; copy: CustomizeCopy }) {
  const hub = useAgents(session.workspace);
  const [draft, setDraft] = useState<AgentDraft>(EMPTY_AGENT);
  // Open form is not the same as an edit: `create` posts a new file, `edit` rewrites one.
  const [mode, setMode] = useState<"create" | "edit" | null>(null);
  const selected = hub.document;

  useEffect(() => {
    if (!selected) return;
    setDraft({
      name: selected.record.name,
      description: selected.record.description,
      instructions: selected.instructions ?? "",
      tools: selected.record.tools ?? [],
    });
  }, [selected]);

  if (!session.workspace) return <p className="muted">{copy.chooseWorkspace}</p>;

  const toggleTool = (tool: string) => setDraft(current => ({
    ...current,
    tools: current.tools.includes(tool) ? current.tools.filter(item => item !== tool) : [...current.tools, tool],
  }));

  const submit = async () => {
    const record = mode === "edit" ? await hub.update(draft) : await hub.create(draft);
    if (record) setMode(null);
  };

  return <div className="skills-layout">
    <section className="skills-main">
      <div className="skills-filter">
        <p className="muted">{copy.agentHint}</p>
        <button className="chip active" data-testid="agent-add"
          onClick={() => { setDraft(EMPTY_AGENT); setMode("create"); hub.select(null); }}>
          {copy.addAgent}
        </button>
      </div>
      {hub.saved.error && <p className="error" role="alert">{copy.error}</p>}
      {!hub.agents.length && <p className="muted">{copy.noAgents}</p>}
      <div className="skill-grid">
        {hub.agents.map(agent => <article key={agent.name}
          className={`skill-card ${hub.selected === agent.name ? "active" : ""}`} data-testid={`agent-card-${agent.name}`}>
          <button className="skill-card-main" aria-pressed={hub.selected === agent.name}
            onClick={() => { hub.select(agent.name); setMode(null); }}>
            <span className="skill-card-head"><b dir="ltr">{agent.name}</b>
              {agent.problem && <span className="skill-badge blocked">{copy.broken}</span>}</span>
            <span className="skill-card-description">{agent.description}</span>
            <span className="skill-card-tags">{(agent.tools ?? []).map(tool => <code key={tool} dir="ltr">{tool}</code>)}</span>
          </button>
        </article>)}
      </div>

      {(mode !== null || hub.saved.proposal) && <form className="agent-form" data-testid="agent-form"
        onSubmit={event => { event.preventDefault(); void submit(); }}>
        <fieldset disabled={hub.saved.busy}>
          <div className="dialog-row">
            <label>{copy.agentName}
              <input dir="ltr" required readOnly={Boolean(selected)}
                pattern="[a-z0-9][a-z0-9-]*" data-testid="agent-name" value={draft.name}
                onChange={event => setDraft({ ...draft, name: event.target.value })} />
            </label>
            <label>{copy.agentDescription}
              <input required data-testid="agent-description" value={draft.description}
                onChange={event => setDraft({ ...draft, description: event.target.value })} />
            </label>
          </div>
          <label>{copy.instructions}
            <textarea rows={8} dir="ltr" data-testid="agent-instructions" value={draft.instructions}
              onChange={event => setDraft({ ...draft, instructions: event.target.value })} />
          </label>
          <fieldset className="tool-picker"><legend>{copy.toolsLabel}</legend>
            {READ_TOOLS.map(tool => <label key={tool} className="check">
              <input type="checkbox" checked={draft.tools.includes(tool)} onChange={() => toggleTool(tool)} />
              <span dir="ltr">{tool}</span>
            </label>)}
          </fieldset>
        </fieldset>
        {hub.saved.proposal && <p role="status" className="warning">{copy.staged} <span className="muted">{copy.stagedHint}</span></p>}
        <div className="dialog-actions">
          <button type="button" onClick={() => { setMode(null); hub.select(null); }}>{copy.cancel}</button>
          <button className="light-button" type="submit" data-testid="agent-submit" disabled={hub.saved.busy}>{copy.save}</button>
        </div>
      </form>}
    </section>

    <aside className="skill-detail" data-testid="agent-detail">
      {!selected ? <p className="muted">{copy.agentDetail}</p> : <>
        <div className="skill-detail-head"><b dir="ltr">{selected.record.name}</b>
          <span className="skill-badge ready">{copy.mine}</span></div>
        <p className="muted">{selected.record.description}</p>
        {selected.record.problem && <p className="error" role="alert">{selected.record.problem}</p>}
        <dl className="skill-facts">
          <div><dt>{copy.toolsLabel}</dt><dd dir="ltr">{(selected.record.tools ?? []).join(", ") || copy.none}</dd></div>
          <div><dt>{copy.source}</dt><dd dir="ltr">{selected.record.path}</dd></div>
        </dl>
        <b>{copy.instructions}</b>
        <pre dir="ltr" className="skill-source">{selected.instructions}</pre>
        <div className="skill-detail-actions">
          <button onClick={() => setMode("edit")} disabled={hub.saved.busy} data-testid="agent-edit">{copy.edit}</button>
          <button className="danger" disabled={hub.saved.busy} data-testid="agent-remove"
            onClick={() => void hub.remove(selected.record.name)}>{copy.remove}</button>
        </div>
      </>}
    </aside>
  </div>;
}
