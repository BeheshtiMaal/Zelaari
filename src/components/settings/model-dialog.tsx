import * as Dialog from "@radix-ui/react-dialog";
import * as Tooltip from "@radix-ui/react-tooltip";
import { XIcon } from "@phosphor-icons/react/dist/csr/X";
import type { Dictionary } from "../../i18n";
import type { ProviderRecord } from "../../lib/protocol";
import type { Session } from "../../lib/use-session";
import { useModelEditor } from "../../lib/use-model-editor";
import { ProbeStatus } from "./probe-status";

export function ModelDialog({ session, existing, t, close }: {session: Session; existing: ProviderRecord | null; t: Dictionary; close(): void}) {
  const editor = useModelEditor(session, existing, close);
  const v = editor.value;
  return <Dialog.Root open onOpenChange={open => { if (!open && !editor.working) close(); }}>
    <Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="model-dialog" onEscapeKeyDown={event => { if (editor.working) event.preventDefault(); }}>
      <div className="dialog-heading"><Dialog.Title>{existing ? t.editModel : t.addModel}</Dialog.Title><Dialog.Close className="icon-button" disabled={editor.working} aria-label={t.close}><XIcon size={20} /></Dialog.Close></div>
      <Dialog.Description className="sr-only">{t.modelsIntro}</Dialog.Description>
      <form onSubmit={event => { event.preventDefault(); void editor.save(); }}>
        <fieldset disabled={editor.working}>
          <label>{t.displayName}<input required maxLength={120} value={v.name} onChange={e => editor.update("name", e.target.value)} autoComplete="off" /></label>
          <div><label>{t.baseUrl}<input required type="url" dir="ltr" value={v.base_url} onChange={e => editor.update("base_url", e.target.value)} autoComplete="off" /></label>
          <div className="presets"><span>{t.fillPreset}</span>{session.presets.map(preset => preset.url ?
            <button className={v.base_url === preset.url ? "selected" : ""} key={preset.name} type="button" onClick={() => editor.update("base_url", preset.url!)}>{preset.name}</button> :
            <Tooltip.Provider key={preset.name}><Tooltip.Root><Tooltip.Trigger asChild><span tabIndex={0} aria-label={`${preset.name}: URL pending`}><button type="button" disabled>{preset.name}</button></span></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="tooltip">URL pending</Tooltip.Content></Tooltip.Portal></Tooltip.Root></Tooltip.Provider>)}</div></div>
          <label>{t.apiKey}<input type="password" dir="ltr" value={v.api_key} required={!existing} autoComplete="new-password" onChange={e => editor.update("api_key", e.target.value)} /><small>{existing ? t.retainKey : t.vaultHelp}</small></label>
          <label>{t.modelName}<input required dir="ltr" maxLength={200} value={v.model} onChange={e => editor.update("model", e.target.value)} autoComplete="off" /><small>{t.modelHelp}</small></label>
          <p className="context-help">{t.contextHelp}</p>
          {editor.result && <ProbeStatus provider={editor.result} t={t} />}
          {editor.error && <p className="error" role="alert">{t.invalidModel}</p>}
          <div className="dialog-actions"><button type="button" onClick={close}>{t.cancel}</button><button type="button" onClick={e => { const form = e.currentTarget.form; if (form?.reportValidity()) void editor.test(); }}>{t.testConnection}</button><button className="light-button" type="submit">{t.save}</button></div>
        </fieldset>
        {editor.working && <p role="status">{t.testing}</p>}
      </form>
    </Dialog.Content></Dialog.Portal>
  </Dialog.Root>;
}
