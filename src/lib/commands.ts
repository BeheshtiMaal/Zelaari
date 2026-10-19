export const commands = ["/grill"] as const;
export function commandMatches(task: string): string[] {
  return /^\/[a-z-]*$/.test(task) ? commands.filter(command => command.startsWith(task)) : [];
}
