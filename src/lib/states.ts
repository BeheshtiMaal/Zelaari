import type { statesCopy } from "../i18n/states";

/** The six empty states the phase promises. */
export const STATE_KEYS = ["noWorkspace", "noModel", "emptyInbox", "noSchedules", "noTasks", "noSkills"] as const;

export type StateKey = (typeof STATE_KEYS)[number];

/**
 * Where each state lives. `null` is a state with no surface yet.
 *
 * The schedules state is the phase's one recorded deviation: this build has no scheduler,
 * so the card and its copy exist and are tested, and Phase 9b puts them on a page. A
 * state wired to a screen that cannot produce it would be worse than an honest `null`.
 */
export const WIRED: Record<StateKey, string | null> = {
  noWorkspace: "home",
  noModel: "home",
  emptyInbox: "inbox",
  noSchedules: null,
  noTasks: "workspace",
  noSkills: "customize/skills",
};

type Copy = ReturnType<typeof statesCopy>;

/** Every state has the same three parts, so a missing one is a test failure, not a blank card. */
export function stateText(copy: Copy, key: StateKey): { label: string; title: string; help: string; primary: string } {
  const state = copy[key];
  return { label: state.label, title: state.title, help: state.help, primary: state.primary };
}
