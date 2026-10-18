import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { createInterface } from "node:readline";

export interface EngineConnection { baseUrl: string; token: string }
export interface Sidecar {
  ready: Promise<EngineConnection>;
  close(): void;
}

export function childEnvironment(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { NODE_ENV: "production" };
  for (const key of ["SystemRoot", "WINDIR", "TEMP", "TMP", "PATH", "PATHEXT", "USERPROFILE", "APPDATA", "LOCALAPPDATA"]) {
    if (process.env[key]) env[key] = process.env[key];
  }
  env.PYTHONUTF8 = "1";
  env.LANGSMITH_TRACING = "false";
  env.LANGCHAIN_TRACING_V2 = "false";
  return env;
}

export function startSidecar(root: string, packaged: boolean, onExit: () => void): Sidecar {
  const token = randomBytes(32).toString("hex");
  // Read opt-in provider configuration, then remove it before any child is spawned.
  const provider = {
    CODEHARNESS_API_KEY: process.env.CODEHARNESS_API_KEY,
    CODEHARNESS_BASE_URL: process.env.CODEHARNESS_BASE_URL,
    CODEHARNESS_MODEL: process.env.CODEHARNESS_MODEL,
  };
  for (const key of Object.keys(provider)) delete process.env[key];
  const python = resolve(root, "backend/.venv/Scripts/python.exe");
  const watchdog = resolve(root, "build/engine/watchdog/watchdog.exe");
  const engine = resolve(root, "build/engine/engine/engine.exe");
  const useBundle = packaged || process.env.CODEHARNESS_PACKAGED_ENGINE === "1";
  let child: ChildProcessWithoutNullStreams | undefined;
  let closing = false;
  const ready = new Promise<EngineConnection>((accept, reject) => {
    const timer = setTimeout(() => {
      child?.stdin.end(); reject(new Error("Engine startup timed out"));
    }, 30000);
    const fail = () => { clearTimeout(timer); reject(new Error("Engine unavailable")); };
    if (process.platform !== "win32" || !existsSync(python) && !useBundle) { fail(); return; }
    const executable = existsSync(watchdog) ? watchdog : python;
    const args = existsSync(watchdog) ? [] : [resolve(root, "backend/server/watchdog.py")];
    args.push(...(useBundle ? [engine] : [python, "-m", "server"]));
    child = spawn(executable, args, {
      cwd: resolve(root, "backend"), env: childEnvironment(),
      stdio: ["pipe", "pipe", "pipe"], windowsHide: true,
    });
    child.stdin.on("error", fail);
    child.on("error", fail);
    // Engine logs can include provider diagnostics. Do not forward stderr or persist it.
    child.stderr.resume();
    child.stdin.write(JSON.stringify({ token, provider }) + "\n");
    let first = true;
    createInterface({ input: child.stdout }).on("line", (line) => {
      if (!first) return;
      first = false;
      try {
        const value: unknown = JSON.parse(line);
        if (!value || typeof value !== "object" || !("port" in value) ||
          !Number.isInteger(value.port) || Number(value.port) < 1 || Number(value.port) > 65535) throw new Error();
        clearTimeout(timer);
        accept({ baseUrl: `http://127.0.0.1:${Number(value.port)}`, token });
      } catch { fail(); child?.stdin.end(); }
    });
    child.on("exit", () => { fail(); if (!closing) onExit(); });
  });
  return { ready, close() { closing = true; child?.stdin.end(); } };
}
