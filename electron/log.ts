import { appendFileSync, existsSync, mkdirSync, renameSync, statSync } from "node:fs";
import { join } from "node:path";

export const MAX_LOG_BYTES = 512 * 1024;

/**
 * The main process log: one bounded line per event, with one rotation.
 *
 * It records start and exit facts only. Prompt text, keys and command output never reach it,
 * and a failure to write must never break the app.
 */
export function createLog(directory: string): (message: string) => void {
  const path = join(directory, "main.log");
  return (message: string) => {
    try {
      mkdirSync(directory, { recursive: true });
      if (existsSync(path) && statSync(path).size >= MAX_LOG_BYTES) renameSync(path, `${path}.1`);
      const line = message.replace(/\s+/g, " ").trim().slice(0, 400);
      appendFileSync(path, `${new Date().toISOString()} ${line}\n`, "utf8");
    } catch {
      // A read-only or full disk only costs the log line.
    }
  };
}
