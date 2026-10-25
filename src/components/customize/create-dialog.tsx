"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import { EMPTY_DRAFT, draftFrom, type SkillDraft } from "../../lib/skills";
import type { SkillDetail } from "../../lib/protocol";

export function CreateDialog({ copy, busy, staged, existing, onSave, close }: {
  copy: CustomizeCopy; busy: boolean; staged: boolean; existing: SkillDetail | null;
  onSave(draft: SkillDraft): Promise<unknown>; close(): void;
}) {
  const [draft, setDraft] = useState<SkillDraft>(existing ? draftFrom(existing) : EMPTY_DRAFT);
  const update = (key: keyof SkillDraft, value: string) => setDraft(current => ({ ...current, [key]: value }));
  return <Dialog.Root open onOpenChange={open => { if (!open) close(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="customize-dialog wide" data-testid="create-dialog">
        <div className="dialog-heading">
          <Dialog.Title>{existing ? copy.editTitle : copy.createTitle}</Dialog.Title>
          <Dialog.Close className="icon-button" aria-label={copy.close}>×</Dialog.Close>
        </div>
        <Dialog.Description className="sr-only">{copy.createTitle}</Dialog.Description>
        <form onSubmit={event => { event.preventDefault(); void onSave(draft); }}>
          <fieldset disabled={busy}>
            <div className="dialog-row">
              <label>{copy.name}
                <input dir="ltr" required readOnly={Boolean(existing)} data-testid="skill-name"
                  pattern="[a-z0-9][a-z0-9-]*" value={draft.name}
                  onChange={event => update("name", event.target.value)} />
                <small>{copy.nameHint}</small>
              </label>
              <label>{copy.command}
                <input dir="ltr" data-testid="skill-command" placeholder="/review" value={draft.command}
                  onChange={event => update("command", event.target.value)} />
                <small>{copy.commandHint}</small>
              </label>
            </div>
            <label>{copy.description}
              <input required data-testid="skill-description" value={draft.description}
                onChange={event => update("description", event.target.value)} />
            </label>
            <label>{copy.category}
              <select data-testid="skill-category" value={draft.category}
                onChange={event => update("category", event.target.value)}>
                <option value="coding">{copy.coding}</option>
                <option value="tests">{copy.tests}</option>
                <option value="web">{copy.web}</option>
                <option value="docs">{copy.docs}</option>
                <option value="other">{copy.all}</option>
              </select>
            </label>
            <label>{copy.body}
              <textarea dir="ltr" rows={10} data-testid="skill-body" value={draft.body}
                onChange={event => update("body", event.target.value)} />
            </label>
          </fieldset>
          {staged && <p role="status" className="warning">{copy.staged} <span className="muted">{copy.stagedHint}</span></p>}
          <div className="dialog-actions">
            <button type="button" onClick={close}>{copy.cancel}</button>
            <button className="light-button" type="submit" data-testid="skill-submit" disabled={busy}>{copy.save}</button>
          </div>
        </form>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
