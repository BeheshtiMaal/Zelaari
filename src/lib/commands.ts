import type { SkillCommand } from "./protocol";

/**
 * The picker is driven by the workspace's enabled skills, not a hard-coded list: a
 * command exists only while its skill is installed and switched on.
 */
export function commandMatches(task: string, list: SkillCommand[]): SkillCommand[] {
  if (!/^\/[a-z-]*$/.test(task)) return [];
  return list.filter(item => item.command.startsWith(task));
}

/** The command the task already names, for the composer's active-skill chip. */
export function activeCommand(task: string, list: SkillCommand[]): SkillCommand | null {
  const first = task.trimStart().split(/\s/, 1)[0];
  return list.find(item => item.command === first) ?? null;
}
