import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const allowed = new Set(["CODEHARNESS_BASE_URL", "CODEHARNESS_MODEL", "CODEHARNESS_API_KEY"]);
export function parseProviderEnv(source: string): Record<string, string> {
  const values: Record<string, string> = {};
  for (const line of source.replace(/^\uFEFF/, "").split(/\r?\n/)) {
    const index = line.indexOf("=");
    const name = line.slice(0, index).trim(), value = line.slice(index + 1).trim();
    if (index >= 0 && allowed.has(name) && value) values[name] = value.replace(/^(['"])(.*)\1$/, "$2");
  }
  return values;
}
export function loadProviderConfig(): void {
  if (!process.env.APPDATA) return;
  try {
    const values = parseProviderEnv(readFileSync(resolve(process.env.APPDATA, "CodeHarness/phase1-provider.env"), "utf8"));
    for (const [name, value] of Object.entries(values)) process.env[name] = value;
  } catch { /* Optional Phase 1 file; env-only configuration also works. */ }
}
