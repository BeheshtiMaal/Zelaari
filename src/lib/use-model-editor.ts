import { useState } from "react";
import type { ModelInput, ProviderRecord } from "./protocol";
import type { Session } from "./use-session";
import { connection } from "./desktop";

export function useModelEditor(session: Session, existing: ProviderRecord | null, close: () => void) {
  const [value, setValue] = useState<ModelInput & { api_key: string }>({
    id: existing?.id ?? crypto.randomUUID(), name: existing?.name ?? "", base_url: existing?.base_url ?? "", model: existing?.model ?? "", api_key: "",
  });
  const [working, setWorking] = useState(false), [error, setError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<ProviderRecord | null>(null);
  function update(field: keyof typeof value, text: string) { setValue(previous => ({ ...previous, [field]: text })); setResult(null); setError(false); }
  function payload() { const { api_key, ...metadata } = value; return api_key ? { ...metadata, api_key } : metadata; }
  async function test() {
    setWorking(true); setError(false);
    try { const output = await connection()?.testModelDraft(payload()); setResult(output ?? null); if (!output) setError(true); }
    catch { setError(true); } finally { setWorking(false); }
  }
  async function save() {
    setSaving(true);
    setWorking(true); setError(false);
    if (await session.saveModel(payload())) {
      if (result?.probe?.status === "ok") await session.testModel(value.id);
      setValue(previous => ({ ...previous, api_key: "" })); close();
    } else setError(true);
    setWorking(false);
    setSaving(false);
  }
  return { value, working, saving, error, result, update, test, save };
}
