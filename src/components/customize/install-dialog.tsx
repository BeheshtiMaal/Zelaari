"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import type { CustomizeCopy } from "../../i18n/customize";
import type { InstallKind } from "../../lib/skills";

export function InstallDialog({ copy, busy, staged, onInstall, close }: {
  copy: CustomizeCopy; busy: boolean; staged: boolean;
  onInstall(kind: InstallKind, source: string): Promise<unknown>; close(): void;
}) {
  const [kind, setKind] = useState<InstallKind>("folder");
  const [source, setSource] = useState("");
  return <Dialog.Root open onOpenChange={open => { if (!open) close(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="customize-dialog" data-testid="install-dialog">
        <div className="dialog-heading"><Dialog.Title>{copy.installTitle}</Dialog.Title>
          <Dialog.Close className="icon-button" aria-label={copy.close}>×</Dialog.Close></div>
        <Dialog.Description className="sr-only">{copy.import}</Dialog.Description>
        <form onSubmit={event => { event.preventDefault(); void onInstall(kind, source); }}>
          <fieldset disabled={busy}>
            <label>{copy.kind}
              <select data-testid="install-kind" value={kind} onChange={event => setKind(event.target.value as InstallKind)}>
                <option value="folder">{copy.folder}</option>
                <option value="zip">{copy.zip}</option>
                <option value="git">{copy.git}</option>
              </select>
            </label>
            <label>{copy.path}
              <input dir="ltr" required data-testid="install-source" value={source}
                placeholder={kind === "git" ? "https://host/repo.git" : "/path/to/skill"}
                onChange={event => setSource(event.target.value)} />
            </label>
          </fieldset>
          {staged && <p role="status" className="warning">{copy.staged} <span className="muted">{copy.stagedHint}</span></p>}
          <div className="dialog-actions">
            <button type="button" onClick={close}>{copy.cancel}</button>
            <button className="light-button" type="submit" data-testid="install-submit" disabled={busy}>{busy ? copy.installing : copy.install}</button>
          </div>
        </form>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
