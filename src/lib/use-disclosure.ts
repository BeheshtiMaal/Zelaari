import { create } from "zustand";

interface Disclosure { open: boolean; ended: boolean; active?: boolean }
export function disclosureValue(previous: Disclosure | undefined, active: boolean, terminal: boolean): Disclosure {
  if (!previous) return { open: active && !terminal, ended: terminal, active };
  if (terminal && !previous.ended) return { open: false, ended: true, active };
  if (active && !previous.active && !terminal) return { ...previous, open: true, active };
  return previous;
}
export const useDisclosure = create<{ values: Record<string, Disclosure>; toggle(key: string, value: Disclosure): void }>(set => ({
  values: {}, toggle: (key, value) => set(state => ({ values: { ...state.values, [key]: value } })),
}));
