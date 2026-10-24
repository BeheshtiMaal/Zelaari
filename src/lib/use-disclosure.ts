import { create } from "zustand";

interface Disclosure { open: boolean; ended: boolean; active?: boolean }
export function disclosureValue(previous: Disclosure | undefined, active: boolean, terminal: boolean, attention = false): Disclosure {
  // `attention` marks a finished step that still needs the user: an action interrupted by a
  // stop or crash may have run, so it stays open instead of collapsing into one line.
  if (!previous) return { open: (active && !terminal) || attention, ended: terminal, active };
  if (terminal && !previous.ended) return { open: attention, ended: true, active };
  if (active && !previous.active && !terminal) return { ...previous, open: true, active };
  return previous;
}
export const useDisclosure = create<{ values: Record<string, Disclosure>; toggle(key: string, value: Disclosure): void }>(set => ({
  values: {}, toggle: (key, value) => set(state => ({ values: { ...state.values, [key]: value } })),
}));
