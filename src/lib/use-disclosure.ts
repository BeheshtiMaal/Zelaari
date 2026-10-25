import { create } from "zustand";

interface Disclosure { open: boolean; ended: boolean; active?: boolean }
export function disclosureValue(previous: Disclosure | undefined, active: boolean, terminal: boolean, attention = false, autoOpen = true): Disclosure {
  // `attention` marks a finished step that still needs the user: an action interrupted by a
  // stop or crash may have run, so it stays open instead of collapsing into one line. It opens
  // even when `autoOpen` is off, because a hidden decision is worse than a noisy one.
  if (!previous) return { open: attention || (autoOpen && active && !terminal), ended: terminal, active };
  if (terminal && !previous.ended) return { open: attention, ended: true, active };
  if (autoOpen && active && !previous.active && !terminal) return { ...previous, open: true, active };
  return previous;
}
export const useDisclosure = create<{ values: Record<string, Disclosure>; toggle(key: string, value: Disclosure): void }>(set => ({
  values: {}, toggle: (key, value) => set(state => ({ values: { ...state.values, [key]: value } })),
}));
