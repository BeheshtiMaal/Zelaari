"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import type { Session } from "../../lib/use-session";
import { useConnectors } from "../../lib/use-customize";
import type { ConnectorStatus, McpServerInput } from "../../lib/protocol";

const EMPTY: McpServerInput = { name: "", transport: "stdio", command: "", url: "", env_keys: [], enabled: true };

function statusLabel(server: ConnectorStatus, copy: CustomizeCopy): string {
  if (!server.enabled) return copy.disabled;
  if (server.status === "connected") return copy.connected;
  if (server.status === "error") return copy.statusError;
  return copy.disabled;
}

export function ConnectorsTab({ session, copy }: { session: Session; copy: CustomizeCopy }) {
  const hub = useConnectors(session.workspace);
  const [dialog, setDialog] = useState(false);
  const [draft, setDraft] = useState<McpServerInput>(EMPTY);
  const [env, setEnv] = useState("");
  const selected = hub.servers.find(server => server.name === hub.selected) ?? null;
  const shown = hub.tested ?? selected;

  if (!session.workspace) return <p className="muted">{copy.chooseWorkspace}</p>;

  const submit = async () => {
    const payload: McpServerInput = {
      ...draft,
      command: draft.transport === "stdio" ? draft.command : null,
      url: draft.transport === "http" ? draft.url : null,
      env_keys: env.split(",").map(item => item.trim()).filter(Boolean),
    };
    // A proposal is not a save: the dialog stays open with the "waiting for approval"
    // note, the same way an install does, so the person is never told a server exists
    // before they have approved it.
    await hub.add(payload);
  };

  return <div className="skills-layout">
    <section className="skills-main">
      <div className="skills-filter">
        <p className="muted">{copy.serverHint}</p>
        <button className="chip active" data-testid="server-add" onClick={() => { setDraft(EMPTY); setEnv(""); setDialog(true); }}>
          {copy.addServer}
        </button>
      </div>
      {hub.saved.error && <p className="error" role="alert">{copy.error}</p>}
      {!hub.servers.length && <p className="muted">{copy.noServers}</p>}
      <div className="skill-grid">
        {hub.servers.map(server => <article key={server.name}
          className={`skill-card ${hub.selected === server.name ? "active" : ""}`} data-testid={`server-card-${server.name}`}>
          <button className="skill-card-main" aria-pressed={hub.selected === server.name}
            onClick={() => hub.select(server.name)}>
            <span className="skill-card-head">
              <b dir="ltr">{server.name}</b>
              <span className={`skill-badge ${server.status === "connected" ? "ready" : server.status === "error" ? "blocked" : "broken"}`}>
                {statusLabel(server, copy)}
              </span>
            </span>
            <span className="skill-card-description" dir="ltr">{server.display}</span>
            <span className="skill-card-tags"><code dir="ltr">{server.transport}</code>
              <span className="muted">{copy.tools}: {server.tools?.length ?? 0}</span></span>
          </button>
        </article>)}
      </div>
      {dialog && <Dialog.Root open onOpenChange={open => { if (!open) setDialog(false); }}>
        <Dialog.Portal><Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="customize-dialog" data-testid="server-dialog">
            <div className="dialog-heading"><Dialog.Title>{copy.addServer}</Dialog.Title>
              <Dialog.Close className="icon-button" aria-label={copy.close}>×</Dialog.Close></div>
            <Dialog.Description className="sr-only">{copy.serverHint}</Dialog.Description>
            <form onSubmit={event => { event.preventDefault(); void submit(); }}>
              <fieldset disabled={hub.saved.busy}>
                <div className="dialog-row">
                  <label>{copy.serverName}
                    <input dir="ltr" required pattern="[a-z0-9][a-z0-9-]*" data-testid="server-name"
                      value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value })} />
                  </label>
                  <label>{copy.transport}
                    <select data-testid="server-transport" value={draft.transport}
                      onChange={event => setDraft({ ...draft, transport: event.target.value as "stdio" | "http" })}>
                      <option value="stdio">stdio</option>
                      <option value="http">http</option>
                    </select>
                  </label>
                </div>
                {draft.transport === "stdio"
                  ? <label>{copy.serverCommand}
                    <input dir="ltr" required data-testid="server-command" placeholder="node server.js"
                      value={draft.command ?? ""} onChange={event => setDraft({ ...draft, command: event.target.value })} />
                  </label>
                  : <label>{copy.serverUrl}
                    <input dir="ltr" required type="url" data-testid="server-url" placeholder="https://host/mcp"
                      value={draft.url ?? ""} onChange={event => setDraft({ ...draft, url: event.target.value })} />
                  </label>}
                <label>{copy.envKeys}
                  <input dir="ltr" data-testid="server-env" placeholder="GITHUB_TOKEN, HOME"
                    value={env} onChange={event => setEnv(event.target.value)} />
                </label>
              </fieldset>
              {hub.saved.proposal && <p role="status" className="warning">{copy.staged}</p>}
              <div className="dialog-actions">
                <button type="button" onClick={() => setDialog(false)}>{copy.cancel}</button>
                <button className="light-button" type="submit" data-testid="server-submit" disabled={hub.saved.busy}>{copy.save}</button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>}
    </section>

    <aside className="skill-detail" data-testid="server-detail">
      {!shown ? <p className="muted">{copy.connectorDetail}</p> : <>
        <div className="skill-detail-head"><b dir="ltr">{shown.name}</b>
          <span className={`skill-badge ${shown.status === "connected" ? "ready" : shown.status === "error" ? "blocked" : "broken"}`}>
            {statusLabel(shown, copy)}
          </span></div>
        <dl className="skill-facts">
          <div><dt>{copy.transport}</dt><dd dir="ltr">{shown.transport}</dd></div>
          <div><dt>{copy.source}</dt><dd dir="ltr">{shown.display}</dd></div>
          <div><dt>{copy.tools}</dt><dd>{shown.tools?.length ?? 0}</dd></div>
        </dl>
        {shown.error && <p className="error" role="alert" dir="ltr">{shown.error}</p>}
        <div className="skill-detail-actions">
          <button onClick={() => void hub.test(shown.name)} disabled={hub.busy} data-testid="server-test">
            {hub.busy ? copy.testing : copy.test}
          </button>
          <button className="danger" disabled={hub.busy || hub.saved.busy}
            onClick={() => void hub.remove(shown.name)} data-testid="server-remove">{copy.remove}</button>
        </div>
        <b>{copy.tools}</b>
        {(shown.tools?.length ?? 0) === 0
          ? <p className="muted">{copy.noTools}</p>
          : <ul className="tool-list" data-testid="server-tools">
            {shown.tools?.map(tool => <li key={tool.namespaced}>
              <code dir="ltr">{tool.namespaced}</code>
              <span className="muted">{tool.description}</span>
            </li>)}
          </ul>}
      </>}
    </aside>
  </div>;
}
