import { realpath, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { parse, resolve } from "node:path";

export async function validateWorkspace(value: string): Promise<string> {
  const path = await realpath(resolve(value));
  const home = await realpath(homedir());
  if (!(await stat(path)).isDirectory() || path.toLowerCase() === parse(path).root.toLowerCase().replace(/\\$/, "") ||
      path.toLowerCase().replace(/[\\/]+$/, "") === parse(path).root.toLowerCase().replace(/[\\/]+$/, "") ||
      path.toLowerCase() === home.toLowerCase()) throw new Error("Choose a project folder, not a root or home");
  return path;
}
