import type { statesCopy } from "../i18n/states";

/** The six empty states the phase promises. */
export const STATE_KEYS = ["noWorkspace", "noModel", "emptyInbox", "noSchedules", "noTasks", "noSkills"] as const;

export type StateKey = (typeof STATE_KEYS)[number];

/**
 * Where each state lives. `null` would be a state with no surface; there is none left, and
 * the test asserts that, so a state cannot quietly lose its screen.
 */
export const WIRED: Record<StateKey, string | null> = {
  noWorkspace: "home",
  noModel: "home",
  emptyInbox: "inbox",
  noSchedules: "schedule",
  noTasks: "workspace",
  noSkills: "customize/skills",
};

type Copy = ReturnType<typeof statesCopy>;

/** Every state has the same three parts, so a missing one is a test failure, not a blank card. */
export function stateText(copy: Copy, key: StateKey): { label: string; title: string; help: string; primary: string } {
  const state = copy[key];
  return { label: state.label, title: state.title, help: state.help, primary: state.primary };
}
