import * as Dialog from "@radix-ui/react-dialog";
import { useRef } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { XIcon } from "@phosphor-icons/react/dist/csr/X";
import type { Dictionary } from "../../i18n";
import { settingsCopy } from "../../i18n/settings";
import type { ProviderRecord } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { useModelEditor } from "../../lib/use-model-editor";
import { ProbeStatus } from "./probe-status";

export function ModelDialog({ session, existing, t, close }: {session: Session; existing: ProviderRecord | null; t: Dictionary; close(): void}) {
  const editor = useModelEditor(session, existing, close);
  const previousFocus = useRef(document.activeElement as HTMLElement | null);
  const v = editor.value;
  return <Dialog.Root open onOpenChange={open => { if (!open && !editor.saving) close(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="model-dialog" onCloseAutoFocus={event => { event.preventDefault(); if (previousFocus.current?.isConnected) previousFocus.current.focus(); else document.querySelector<HTMLButtonElement>(".settings-heading button")?.focus(); }} onEscapeKeyDown={event => { if (editor.saving) event.preventDefault(); }}>
      <div className="dialog-heading"><Dialog.Title>{existing ? t.editModel : t.addModel}</Dialog.Title><Dialog.Close className="icon-button" disabled={editor.saving} aria-label={t.close}><XIcon size={20} /></Dialog.Close></div>
      <Dialog.Description className="sr-only">{settingsCopy(session.locale).intro.models}</Dialog.Description>
      <form onSubmit={event => { event.preventDefault(); void editor.save(); }}>
        <fieldset disabled={editor.working}>
          <label>{t.displayName}<input aria-label={t.displayName} required maxLength={120} value={v.name} onChange={e => editor.update("name", e.target.value)} autoComplete="off" /></label>
          <div><label>{t.baseUrl}<input aria-label={t.baseUrl} required type="url" dir="ltr" value={v.base_url} onChange={e => editor.update("base_url", e.target.value)} autoComplete="off" /></label>
          <div className="presets"><span>{t.fillPreset}</span>{session.presets.map(preset => preset.url ?
            <button className={v.base_url === preset.url ? "selected" : ""} key={preset.name} type="button" onClick={() => editor.update("base_url", preset.url!)}>{preset.name}</button> :
            <Tooltip.Provider key={preset.name}><Tooltip.Root><Tooltip.Trigger asChild><span tabIndex={0} aria-label={`${preset.name}: URL pending`}><button type="button" disabled>{preset.name}</button></span></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="tooltip">URL pending</Tooltip.Content></Tooltip.Portal></Tooltip.Root></Tooltip.Provider>)}</div></div>
          <label>{t.apiKey}<input aria-label={t.apiKey} aria-describedby="key-help" type="password" dir="ltr" value={v.api_key} required={!existing} autoComplete="new-password" onChange={e => editor.update("api_key", e.target.value)} /><small id="key-help">{existing ? t.retainKey : t.vaultHelp}</small></label>
          <label>{t.modelName}<input aria-label={t.modelName} aria-describedby="model-help" required dir="ltr" maxLength={200} value={v.model} onChange={e => editor.update("model", e.target.value)} autoComplete="off" /><small id="model-help">{t.modelHelp}</small></label>
          <p className="context-help">{t.contextHelp}</p>
          {editor.result && <ProbeStatus provider={editor.result} t={t} />}
          {editor.error && <p className="error" role="alert">{t.invalidModel}</p>}
        </fieldset>
        <div className="dialog-actions"><button type="button" disabled={editor.saving} onClick={close}>{t.cancel}</button><button type="button" disabled={editor.working} onClick={e => { const form = e.currentTarget.form; if (form?.reportValidity()) void editor.test(); }}>{t.testConnection}</button><button className="light-button" disabled={editor.working} type="submit">{t.save}</button></div>
        {editor.working && <p role="status">{t.testing}</p>}
      </form>
    </Dialog.Content></Dialog.Portal>
  </Dialog.Root>;
}
