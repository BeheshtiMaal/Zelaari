import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { _electron as electron, expect, type ElectronApplication, type Page } from "@playwright/test";

/**
 * The Phase 10 walkthrough: the app as a person installs it.
 *
 * This launches `dist/win-unpacked/CodeHarness.exe` — the packaged tree, not the checkout —
 * and checks the four claims of a first run (requirements R8, R9): Persian, a demo model
 * with no key, the sample project that carries `read-framework-docs`, and a demo task that
 * returns a real tool result. Then it closes the window and asserts nothing survives.
 *
 * `scripts/smoke-installer.py` covers the parts a window cannot show (no Python or Node in
 * the tree, no secrets, the engine's own auth). Neither test repeats the other.
 *
 * Run: npx tsx tests/phase10-desktop.ts
 */

const root = process.cwd();
const executable = resolve(root, "dist/win-unpacked/CodeHarness.exe");
const artifacts = resolve(root, "artifacts");
await mkdir(artifacts, { recursive: true });
const profile = await mkdtemp(resolve(tmpdir(), "codeharness-phase10-"));
const python = resolve(root, "backend/.venv/Scripts/python.exe");
const marker = "cedar-phase10";
const evidence: Record<string, unknown> = {};

function survivors(pids: number[]): number[] {
  return JSON.parse(execFileSync(python, ["-c", "import psutil,json,sys; print(json.dumps([p for p in json.loads(sys.argv[1]) if psutil.pid_exists(p)]))", JSON.stringify(pids)], { encoding: "utf8" })) as number[];
}

function engineProcesses(pid: number): number[] {
  const script = "import psutil,json,sys; p=psutil.Process(int(sys.argv[1])); print(json.dumps([c.pid for c in p.children(recursive=True) if c.name().lower() in {'engine.exe','watchdog.exe'}]))";
  return JSON.parse(execFileSync(python, ["-c", script, String(pid)], { encoding: "utf8" })) as number[];
}

async function launch(): Promise<ElectronApplication> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  }
  // No CODEHARNESS_PACKAGED_ENGINE: a packaged build must choose the bundle by itself.
  return electron.launch({ executablePath: executable, args: [], env: { ...env, CODEHARNESS_LANGUAGE: "fa", CODEHARNESS_TEST_USER_DATA: profile }, timeout: 180000 });
}

const app = await launch();
const pids: number[] = [];
try {
  const page: Page = await app.firstWindow();
  page.setDefaultTimeout(60000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.name));
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 120000 });

  // R8: Persian on the first run, and the right direction for it.
  assert.equal(await page.evaluate(() => document.documentElement.dir), "rtl");
  assert.equal(await page.evaluate(() => document.documentElement.lang), "fa");

  // R8: a model is ready with no key typed and no network.
  const models = await page.locator(".model-select select option").evaluateAll(nodes => nodes.map(node => (node as HTMLOptionElement).value));
  assert.ok(models.includes("demo"), `the demo model should be offered, got ${models.join(",")}`);
  await page.locator(".model-select select").selectOption("demo");
  evidence.models = models;

  // R9: the sample project, opened from the bundle the installer laid down.
  await page.getByTestId("state-sample-project").click();
  const sample = resolve(profile, "sample-project");
  const skill = resolve(sample, ".harness/skills/read-framework-docs/SKILL.md");
  // The empty state that offered the sample is gone, and the copy is on disk with its skill:
  // the run below reads this folder, so a stale one would not answer with the sample's text.
  await expect(page.getByTestId("state-sample-project")).toHaveCount(0);
  assert.ok((await readFile(skill, "utf8")).includes("read-framework-docs"), "the sample's project skill was not copied");
  evidence.sample = { copied: sample, skill: true };

  // A marker only this run can see, so a tool result cannot be the model talking. It goes
  // first because the demo model summarises the head of the file, not the whole of it.
  const readme = resolve(sample, "README.md");
  await writeFile(readme, `marker=${marker}\n\n${await readFile(readme, "utf8")}`);
  await page.locator("#task").fill("read README.md and summarize");
  const created = page.waitForResponse(response => new URL(response.url()).pathname === "/runs" && response.request().method() === "POST");
  await page.locator("button[type=submit]").click();
  const runId = ((await (await created).json()) as { run_id: string }).run_id;
  await expect(page.getByTestId("tool-line")).toBeVisible({ timeout: 90000 });
  await expect(page.getByTestId("keyvalue")).toContainText(marker, { timeout: 30000 });
  await expect(page.locator(".stop")).toBeDisabled({ timeout: 15000 });
  evidence.run = runId;
  await page.screenshot({ path: resolve(artifacts, "phase10-first-run.png") });
  assert.deepEqual(errors, []);

  pids.push(...engineProcesses(app.process().pid!));
  assert.ok(pids.length >= 2, `the packaged app should run a watchdog and an engine, saw ${pids.length}`);
  evidence.processes = pids;
} finally {
  await app.close();
}

// R8's other half: closing the window is the whole quit.
const alive = survivors(pids);
assert.deepEqual(alive, [], `processes outlived the packaged app: ${alive.join(",")}`);
evidence.survivors = alive;
console.log("Phase 10 walkthrough passed:", JSON.stringify(evidence));
