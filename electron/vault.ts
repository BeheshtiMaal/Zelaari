import { readFile, mkdir, writeFile, rename } from "node:fs/promises";
import { dirname } from "node:path";
import { z } from "zod";

export interface Encryption {
  isEncryptionAvailable(): boolean;
  encryptString(value: string): Buffer;
  decryptString(value: Buffer): string;
}
const entries = z.record(z.string(), z.string());
export class Vault {
  constructor(private path: string, private encryption: Encryption) {}
  private async read(): Promise<Record<string, string>> {
    try { return entries.parse(JSON.parse(await readFile(this.path, "utf8"))); }
    catch (error) { if ((error as NodeJS.ErrnoException).code === "ENOENT") return {}; throw new Error("Vault unavailable"); }
  }
  private check() { if (!this.encryption.isEncryptionAvailable()) throw new Error("Vault unavailable"); }
  async put(id: string, key: string): Promise<void> {
    this.check();
    const values = await this.read();
    values[id] = this.encryption.encryptString(key).toString("base64");
    await mkdir(dirname(this.path), { recursive: true });
    await writeFile(this.path + ".tmp", JSON.stringify(values), { mode: 0o600 });
    await rename(this.path + ".tmp", this.path);
  }
  async all(): Promise<Record<string, string>> {
    const values = await this.read();
    if (Object.keys(values).length) this.check();
    return Object.fromEntries(Object.entries(values).map(([id, encrypted]) =>
      [id, this.encryption.decryptString(Buffer.from(encrypted, "base64"))]));
  }
}

export const modelSubmission = z.object({
  id: z.string().regex(/^[a-zA-Z0-9_-]{1,64}$/).refine(id => id !== "demo"),
  name: z.string().trim().min(1).max(120), model: z.string().trim().min(1).max(200),
  base_url: z.string().refine(value => {
    try { const u = new URL(value); return ["http:", "https:"].includes(u.protocol) && !u.username && !u.password && !u.search && !u.hash; }
    catch { return false; }
  }), api_key: z.string().min(1).max(16384).optional(),
}).strict();
export function trustedFrame(url: string | undefined): boolean {
  try { const u = new URL(url ?? ""); return u.protocol === "app:" && u.hostname === "codeharness" && !u.port && !u.username && !u.password; }
  catch { return false; }
}
