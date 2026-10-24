export type CommandResult = {
  output: string;
  exitCode: number | null;
  timedOut: boolean;
  timeoutSeconds: number;
  truncated: boolean;
  totalLines: number;
};

/** Read a `run_command` result. Anything else is not a terminal, so it stays text. */
export function commandResult(text: string): CommandResult | null {
  let value: unknown;
  try { value = JSON.parse(text); } catch { return null; }
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  if (typeof record.output !== "string" || !("exit_code" in record)) return null;
  return {
    output: record.output,
    exitCode: typeof record.exit_code === "number" ? record.exit_code : null,
    timedOut: record.timed_out === true,
    timeoutSeconds: typeof record.timeout_seconds === "number" ? record.timeout_seconds : 0,
    truncated: record.truncated === true,
    totalLines: typeof record.total_lines === "number" ? record.total_lines : 0,
  };
}

/** The part of the output the panel shows before "show more". */
export function visibleOutput(result: CommandResult, limit: number): { text: string; hidden: number } {
  const lines = result.output.replace(/\r\n/g, "\n").split("\n");
  if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  const shown = lines.slice(0, Math.max(1, limit));
  return { text: shown.join("\n"), hidden: Math.max(0, lines.length - shown.length) };
}

export function killNote(seconds: number, copy: { killed: string; silent: string }): string {
  const number = new Intl.NumberFormat("en", { maximumFractionDigits: 0 }).format(seconds);
  return `\n${copy.silent.replace("{seconds}", number)}\n${copy.killed}`;
}
