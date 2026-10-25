import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { _electron as electron, expect, type ElectronApplication } from "@playwright/test";
import { initialRun, reduceEvent } from "../src/store/run";
import type { HarnessEvent } from "../src/lib/protocol";

const root = process.cwd();
const artifacts = resolve(root, "artifacts");
await mkdir(artifacts, { recursive: true });
const workspace = await mkdtemp(resolve(tmpdir(), "codeharness-desktop-"));
await writeFile(resolve(workspace, "README.md"), "# Walking skeleton\nReal desktop read marker: silver-maple.\n");
const python = resolve(root, "backend/.venv/Scripts/python.exe");

function processSnapshot(pid: number): { pids: number[]; bound: string[] } {
  // Inspect only our process tree. Do not include command arguments/environments.
  const script = "import psutil,json,sys; p=psutil.Process(int(sys.argv[1])); children=[c for c in p.children(recursive=True) if c.name().lower() in {'python.exe','pythonw.exe','engine.exe','watchdog.exe'}]; print(json.dumps({'pids':[c.pid for c in children], 'bound':[x.laddr.ip for c in children for x in c.net_connections(kind='inet') if x.status=='LISTEN']}))";
  return JSON.parse(execFileSync(python, ["-c", script, String(pid)], { encoding: "utf8" }));
}
function survivors(pids: number[]): number[] {
  return JSON.parse(execFileSync(python, ["-c", "import psutil,json,sys; print(json.dumps([p for p in json.loads(sys.argv[1]) if psutil.pid_exists(p)]))", JSON.stringify(pids)], { encoding: "utf8" }));
}
async function launch(language: "fa" | "en", packaged = false): Promise<ElectronApplication> {
  const userData = await mkdtemp(resolve(tmpdir(), "codeharness-profile-"));
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  }
  return electron.launch({ args: [root], env: { ...env, CODEHARNESS_LANGUAGE: language, CODEHARNESS_TEST_USER_DATA: userData, CODEHARNESS_PACKAGED_ENGINE: packaged ? "1" : "0" }, timeout: 120000 });
}

const evidence: Record<string, unknown> = {};
for (const language of ["fa", "en"] as const) {
  const app = await launch(language);
  let pids: number[] = [];
  try {
    await expect.poll(() => app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0]?.isVisible() ?? false), { timeout: 3000 }).toBe(true);
    const native = await app.evaluate(({ BrowserWindow }) => ({ visible: BrowserWindow.getAllWindows()[0]?.isVisible(), seconds: process.uptime() }));
    evidence[`${language}-native-window`] = native;
    assert.equal(native.visible, true);
    assert.ok(native.seconds < 3, "The native app window must open in under three seconds");
    // Process startup and test instrumentation overhead are reported separately.
    const page = await app.firstWindow();
    page.setDefaultTimeout(15000);
    const errors: string[] = [];
    page.on("pageerror", error => {
      errors.push(error.name);
      console.log("Renderer error:", error.stack);
    });
    const failedRequests: string[] = [];
    page.on("requestfailed", request => failedRequests.push(new URL(request.url()).pathname));
    await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 30000 });
    if (language === "en") {
      await page.locator(".settings").click();
      await page.locator(".settings-nav button").nth(1).click();
      await page.getByRole("button", {name: "English", exact: true}).click();
      await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
      await page.locator(".sidebar nav button").first().click();
    }
    let releaseHealth!: () => void;
    let capturedHealth!: () => void;
    const captured = new Promise<void>(resolve => { capturedHealth = resolve; });
    const healthGate = new Promise<void>(resolve => { releaseHealth = resolve; });
    await page.route("**/health", async route => { capturedHealth(); await healthGate; await route.continue(); });
    const reloaded = page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await captured;
    await expect(page.locator("#task")).toBeDisabled();
    releaseHealth();
    await reloaded;
    await expect(page.locator("#task")).toBeEnabled({ timeout: 10000 });
    await page.unroute("**/health");
    assert.equal(await page.evaluate(() => document.documentElement.dir), language === "fa" ? "rtl" : "ltr");
    assert.equal(await page.evaluate(() => typeof (window as unknown as { require?: unknown }).require), "undefined");
    assert.deepEqual(await page.evaluate(() => Object.keys(window.harness ?? {}).sort()), ["appInfo", "baseUrl", "clearKeys", "onEngineStatus", "openLogFolder", "pickWorkspace", "restartEngine", "revealAppData", "revealWorkspace", "saveModel", "testModelDraft", "token", "vaultStatus"]);
    await expect(page.locator(".sidebar button:disabled")).toHaveCount(1);
    await page.screenshot({ path: resolve(artifacts, `home-${language}.png`) });
    const body = await page.locator("body").boundingBox();
    const sidebar = await page.locator(".sidebar").boundingBox();
    assert.ok(body && sidebar);
    assert.ok(language === "fa" ? sidebar.x > body.width / 2 : sidebar.x < body.width / 2);
    // R15: the reference size, in both directions, with nothing hanging off the edge.
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const overflow = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: innerWidth }));
    assert.ok(overflow.scroll <= overflow.width, `${language} overflows horizontally: ${overflow.scroll} > ${overflow.width}`);
    const toolbar = await page.locator(".composer-toolbar > *").evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().x));
    assert.ok(toolbar.length >= 2, "the composer toolbar should have two ends");
    assert.ok(language === "fa" ? toolbar[0] > toolbar[toolbar.length - 1] : toolbar[0] < toolbar[toolbar.length - 1], `${language} composer should mirror`);
    // R14: the first thing Tab reaches is the way past the sidebar.
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.press("Tab");
    await expect(page.getByTestId("skip-link")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main")).toBeFocused();
    assert.equal(await page.locator(".surface").evaluate(element => getComputedStyle(element).borderRadius), "24px");
    evidence[`${language}-scroll-return`] = await page.locator(".surface").evaluate(element => {
      const returned: unknown = element.scrollIntoView({ block: "end" });
      return { type: typeof returned, isPromise: returned instanceof Promise };
    });
    await app.evaluate(({ dialog }, selected) => {
      dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [selected] });
    }, workspace);
    await page.getByTestId("pick-workspace").click();
    await page.locator(".model-select select").selectOption("demo");
    await page.locator("#task").fill("read README.md and summarize");
    const created = page.waitForResponse(response => new URL(response.url()).pathname === "/runs" && response.request().method() === "POST");
    await page.locator("button[type=submit]").click();
    const createdRun = await (await created).json() as { run_id: string };
    try { await expect(page.getByTestId("tool-line")).toBeVisible({ timeout: 45000 }); }
    catch (error) { await page.screenshot({ path: resolve(artifacts, "desktop-failure.png") }); throw error; }
    await expect(page.getByTestId("callout")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("keyvalue")).toContainText("silver-maple");
    await expect(page.locator(".stop")).toBeDisabled({ timeout: 5000 });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await expect(page.getByTestId("fallback")).toHaveCount(0);
    await page.screenshot({ path: resolve(artifacts, `run-${language}.png`) });
    const connection = await page.evaluate(() => ({ baseUrl: window.harness!.baseUrl, token: window.harness!.token }));
    const invalid = await fetch(`${connection.baseUrl}/health`);
    assert.equal(invalid.status, 401);
    const snapshot = processSnapshot(app.process().pid!); pids = snapshot.pids;
    assert.ok(snapshot.bound.length > 0 && snapshot.bound.every(ip => ip === "127.0.0.1"));
    evidence[`${language}-binding`] = snapshot.bound;
    const listeners = execFileSync("netstat", ["-ano", "-p", "tcp"], { encoding: "utf8" }).split(/\r?\n/).filter(line => line.includes("LISTENING") && snapshot.pids.includes(Number(line.trim().split(/\s+/).at(-1))));
    assert.ok(listeners.length > 0 && listeners.every(line => line.includes("127.0.0.1:")));
    evidence[`${language}-netstat`] = listeners.map(line => line.trim());
    assert.deepEqual(errors, []);
    assert.deepEqual(failedRequests, []);

    // Replay the actual persisted events and check the same visible data.
    const log = await readFile(resolve(workspace, ".harness/runs", createdRun.run_id, "events.jsonl"), "utf8");
    const events = log.trim().split(/\r?\n/).map(line => JSON.parse(line) as HarnessEvent);
    const replay = events.reduce(reduceEvent, initialRun);
    assert.equal(replay.status, "completed");
    assert.ok(replay.items.some(item => item.kind === "message" && item.text.includes("silver-maple")));
    assert.ok(!log.includes(connection.token));
    assert.ok(!page.url().includes(connection.token));
    evidence[`${language}-events`] = events.length;
    if (language === "fa") {
      await page.locator(".nav-item.active").click();
      await page.route("**/events", async route => {
        const id = new URL(route.request().url()).pathname.split("/")[2];
        const make = (seq: number, type: string, payload: object) => ({ run_id: id, seq, type, ts: new Date().toISOString(), ...payload });
        const malformed = [make(1, "run.started", { task: "Malformed fixture", model: "demo" }), make(2, "message.delta", { message_id: "bad", text: 'root = Missing("Readable fallback");' }), make(3, "run.finished", { status: "completed" })];
        await route.fulfill({ contentType: "text/event-stream", body: malformed.map(event => `data: ${JSON.stringify(event)}\n\n`).join("") });
      });
      await page.locator("#task").fill("read README.md");
      await page.locator("button[type=submit]").click();
      await expect(page.getByTestId("fallback")).toContainText("Readable fallback", { timeout: 15000 });
      await page.screenshot({ path: resolve(artifacts, "malformed-fa.png") });
      evidence["malformed-fallback"] = true;
    }
  } finally { await app.close(); }
  await expect.poll(() => survivors(pids), { timeout: 5000 }).toEqual([]);
  evidence[`${language}-normal-cleanup`] = true;
}

// Kill only Electron main. The private pipe must close and kill the job members.
for (const packaged of [false, true]) {
  const app = await launch("fa", packaged);
  let owned: number[] = [];
  try {
    const page = await app.firstWindow();
    page.setDefaultTimeout(15000);
    await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 30000 });
    const mainPid = await app.evaluate(() => process.pid);
    owned = processSnapshot(mainPid).pids;
    assert.ok(owned.length > 0, "The engine must be alive before forced termination");
    execFileSync("taskkill", ["/PID", String(mainPid), "/F"], { windowsHide: true });
    await expect.poll(() => survivors(owned), { timeout: 5000 }).toEqual([]);
    evidence[packaged ? "packaged-forced-cleanup" : "dev-forced-cleanup"] = true;
  } finally { await app.close().catch(() => {}); }
}

await writeFile(resolve(artifacts, "desktop.json"), JSON.stringify(evidence, null, 2));
console.log("Desktop: Persian/English, real demo read + OpenUI, replay, auth, loopback, normal and forced cleanup passed.");
