import { app } from "electron";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { resolve } from "node:path";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";

app.setPath("userData", mkdtempSync(resolve(tmpdir(), "codeharness-sidecar-")));
app.disableHardwareAcceleration();

const token = process.env.SPIKE_TOKEN;
delete process.env.SPIKE_TOKEN;
if (!token) app.exit(2);
app.whenReady().then(() => {
  const pythonRoot = resolve(__dirname, "../../python");
  const child = spawn(resolve(pythonRoot, "dist/job_launcher/job_launcher.exe"), [
    resolve(pythonRoot, "dist/sidecar/sidecar.exe"),
  ], { stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
  child.stdin.write(token + "\n");
  let first = true;
  createInterface({ input: child.stdout }).on("line", line => {
    if (first) {
      first = false;
      const value: unknown = JSON.parse(line);
      if (!value || typeof value !== "object" || !("port" in value)) {
        child.stdin.end(); app.exit(2); return;
      }
      process.stdout.write(JSON.stringify({ ...value, first_stdout_line: true }) + "\n");
    } else if (JSON.parse(line).quit === true) app.quit();
  });
  child.stderr.pipe(process.stderr);
  child.on("error", () => { child.stdin.end(); app.exit(2); });
  child.on("exit", code => { if (code) app.exit(code); });
  app.on("before-quit", () => child.stdin.end());
});
