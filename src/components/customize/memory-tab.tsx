"use client";
import type { CustomizeCopy } from "../../i18n/customize";
import type { Session } from "../../lib/use-session";
import { useMemory } from "../../lib/use-customize";
import { localeDigits } from "../../lib/localised-number";

export function MemoryTab({ session, copy }: { session: Session; copy: CustomizeCopy }) {
  const memory = useMemory(session.workspace);
  if (!session.workspace) return <p className="muted">{copy.chooseWorkspace}</p>;
  const bytes = new TextEncoder().encode(memory.draft).length;
  const limit = memory.document?.limit ?? 32768;
  return <div className="skills-layout">
    <section className="skills-main">
      <div className="skills-filter"><p className="muted">{copy.memoryHint}</p></div>
      <form className="memory-form" onSubmit={event => { event.preventDefault(); void memory.save(); }}>
        <label className="sr-only" htmlFor="memory-body">{copy.memoryTitle}</label>
        <textarea id="memory-body" dir="auto" rows={16} data-testid="memory-body"
          value={memory.draft} disabled={memory.loading}
          placeholder={copy.memoryEmpty}
          onChange={event => memory.setDraft(event.target.value)} />
        <div className="memory-footer">
          <span className="muted" data-testid="memory-bytes">
            {localeDigits(bytes, session.locale)} {copy.memoryBytes} {localeDigits(limit, session.locale)}
          </span>
          <div className="dialog-actions">
            <button type="button" onClick={() => void memory.load()}>{copy.refresh}</button>
            <button className="light-button" type="submit" data-testid="memory-save"
              disabled={memory.loading || bytes > limit}>{copy.memorySave}</button>
          </div>
        </div>
        {memory.error && <p className="error" role="alert">{copy.error}</p>}
        {memory.proposal && <p role="status" className="warning">{copy.staged} <span className="muted">{copy.stagedHint}</span></p>}
      </form>
    </section>
    <aside className="skill-detail">
      <div className="skill-detail-head"><b>{copy.memoryTitle}</b></div>
      <p className="muted">{copy.memoryHint}</p>
      <dl className="skill-facts">
        <div><dt>{copy.contextCost}</dt><dd>{localeDigits(bytes, session.locale)} / {localeDigits(limit, session.locale)}</dd></div>
      </dl>
    </aside>
  </div>;
}
