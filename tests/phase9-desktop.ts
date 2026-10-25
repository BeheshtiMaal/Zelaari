import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { _electron as electron, expect, type ElectronApplication, type Page } from "@playwright/test";

/**
 * The Phase 9 walkthrough (S1–S8).
 *
 * Each step is a claim from `requirements.md` turned into something the machine can check:
 * the settings screens show what the engine enforces, the appearance reaches the shell and
 * survives a relaunch, a destructive row needs two confirmations, a rendered program really
 * renders, and a dead engine comes back. Screenshots are evidence, not the assertion.
 */

const root = process.cwd();
const artifacts = resolve(root, "artifacts");
await mkdir(artifacts, { recursive: true });
const python = resolve(root, "backend/.venv/Scripts/python.exe");
const profile = await mkdtemp(resolve(tmpdir(), "codeharness-phase9-"));
const evidence: Record<string, unknown> = {};
const version = JSON.parse(await readFile(resolve(root, "package.json"), "utf8")) as { version: string };

function enginePids(pid: number): number[] {
  const script = "import psutil,json,sys; p=psutil.Process(int(sys.argv[1])); print(json.dumps([c.pid for c in p.children(recursive=True) if c.name().lower() in {'python.exe','pythonw.exe','engine.exe','watchdog.exe'}]))";
  return JSON.parse(execFileSync(python, ["-c", script, String(pid)], { encoding: "utf8" })) as number[];
}

async function launch(language: "fa" | "en", userData = profile): Promise<ElectronApplication> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  }
  return electron.launch({ args: [root], env: { ...env, CODEHARNESS_LANGUAGE: language, CODEHARNESS_TEST_USER_DATA: userData, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
}

async function ready(app: ElectronApplication): Promise<Page> {
  const page = await app.firstWindow();
  page.setDefaultTimeout(30000);
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
  return page;
}

const section = async (page: Page, index: number) => {
  await page.locator(".settings").click();
  await page.locator(".settings-nav button").nth(index).click();
};
const home = async (page: Page) => { await page.locator(".sidebar nav button").first().click(); };

// ── S1–S2 and S7 in one Persian session ──────────────────────────────────────────────────
const first = await launch("fa");
try {
  const page = await ready(first);
  await page.getByTestId("state-sample-project").click();
  await expect(page.getByTestId("state-sample-project")).toBeHidden({ timeout: 60000 });

  // S1: the seven sections the mock draws, each one opening with a heading and no error.
  await page.locator(".settings").click();
  const nav = page.locator(".settings-nav button");
  assert.equal(await nav.count(), 7, "the mock has seven settings sections");
  for (let index = 0; index < 7; index++) {
    await nav.nth(index).click();
    await expect(page.locator(".settings-content h2").first()).toBeVisible();
  }
  await nav.nth(0).click();
  await expect(page.getByTestId("model-card").first()).toBeVisible();
  await nav.nth(1).click();
  await expect(page.getByTestId("appearance-display")).toBeVisible();
  await expect(page.getByTestId("appearance-activity")).toBeVisible();
  await nav.nth(2).click();
  await expect(page.getByTestId("always-ask")).toBeVisible();
  await nav.nth(5).click();
  // Persian digits in the danger row: the run count is formatted for the locale.
  const runsHelp = await page.getByTestId("data-danger").innerText();
  assert.match(runsHelp, /[۰-۹]/, `the run count should use Persian digits: ${runsHelp}`);
  evidence["s1-sections"] = await nav.allInnerTexts();
  await page.screenshot({ path: resolve(artifacts, "phase9-s1-settings.png") });

  // S2: an appearance change reaches the shell now, and is still there after a relaunch.
  await nav.nth(1).click();
  await page.getByTestId("appearance-theme").getByRole("button").nth(1).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByTestId("appearance-font").getByRole("button").nth(2).click();
  await expect(page.locator("html")).toHaveAttribute("data-font", "large");
  const scale = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--fs-scale").trim());
  assert.equal(scale, "1.12");
  await page.screenshot({ path: resolve(artifacts, "phase9-s2-light-large.png") });
  evidence["s2-scale"] = scale;

  // S7: the engine dies, the card says so, and the restart brings it back.
  const pid = first.process().pid;
  if (pid === undefined) throw new Error("no main process pid");
  for (const child of enginePids(pid)) process.kill(child);
  await expect(page.getByTestId("crash-card")).toBeVisible({ timeout: 30000 });
  const overlay = await page.locator(".crash-overlay").boundingBox();
  const viewport = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
  assert.ok(overlay && overlay.width >= viewport.width - 1 && overlay.height >= viewport.height - 1, "the crash card covers the window");
  assert.ok(!(await page.getByTestId("crash-card").innerText()).match(/[0-9a-f]{32}/i), "the crash card shows no token");
  await page.screenshot({ path: resolve(artifacts, "phase9-s7-crash.png") });
  await page.getByTestId("restart-engine").click();
  await expect(page.getByTestId("crash-card")).toBeHidden({ timeout: 120000 });
  // The renderer's own client, on the new port and token: the sample route answers.
  await expect(page.getByTestId("state-sample-project")).toHaveCount(0);
  await page.locator(".settings").click();
  await expect(page.locator(".settings-nav button").first()).toBeVisible({ timeout: 30000 });
  evidence["s7-restarted"] = true;
} finally {
  await first.close();
}

// ── S3–S6 in a second Persian session on the same profile ────────────────────────────────
const second = await launch("fa");
try {
  const page = await ready(second);
  // The sample workspace is what the destructive row and the demo run need; select it again
  // if this profile did not restore the last one.
  if (await page.getByTestId("state-sample-project").isVisible().catch(() => false)) {
    await page.getByTestId("state-sample-project").click();
    await expect(page.getByTestId("state-sample-project")).toBeHidden({ timeout: 60000 });
  }

  // S2 continued: the theme and the font survived the relaunch.
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.locator("html")).toHaveAttribute("data-font", "large");

  // S3: the five locked rows the engine enforces, the rules table, and a threshold that asks.
  await section(page, 2);
  for (const key of ["storage", "web", "commands", "mcp", "timeout"]) {
    await expect(page.getByTestId(`locked-${key}`)).toBeVisible();
  }
  assert.equal(await page.locator("[data-testid^='locked-']").count(), 5, "the mock's three plus MCP and timeouts");
  await expect(page.getByTestId("rules-grid")).toBeVisible();
  await expect(page.getByTestId("plan-approval")).toBeVisible();
  await page.getByTestId("plan-steps").fill("9");
  await page.getByTestId("plan-save").click();
  await expect(page.getByTestId("approval-card")).toBeVisible({ timeout: 20000 });
  evidence["s3-approval"] = (await page.getByTestId("approval-card").innerText()).slice(0, 120);
  await page.screenshot({ path: resolve(artifacts, "phase9-s3-permissions.png") });

  // S4: real paths, a retention that sticks, and a danger zone that needs both confirmations.
  await section(page, 5);
  const location = await page.getByTestId("data-location").innerText();
  assert.match(location, /[A-Za-z]:\\|\\/, `the app data path should be shown: ${location}`);
  await page.getByTestId("retention-select").selectOption("30");
  await expect(page.getByTestId("retention-select")).toHaveValue("30");
  const before = await page.getByTestId("data-danger").innerText();
  await page.getByTestId("data-danger").getByRole("button").first().click();
  await expect(page.getByTestId("confirm-dialog")).toBeVisible();
  await expect(page.getByTestId("confirm-action")).toBeDisabled();
  await page.getByTestId("confirm-acknowledge").check();
  await expect(page.getByTestId("confirm-action")).toBeEnabled();
  await page.screenshot({ path: resolve(artifacts, "phase9-s4-confirm.png") });
  await page.getByTestId("confirm-dialog").locator("button.light-button").click();
  await expect(page.getByTestId("confirm-dialog")).toBeHidden();
  assert.equal(await page.getByTestId("data-danger").innerText(), before, "cancelling writes nothing");
  evidence["s4-paths"] = location.split("\n").filter(line => line.includes(":")).slice(0, 3);

  // S5: the running version, and a log folder the button really reaches.
  await section(page, 6);
  // The row shows an em dash until `appInfo` answers, so wait for the version rather than
  // reading the placeholder.
  await expect(page.getByTestId("about-version")).toHaveText(version.version, { timeout: 30000 });
  await expect(page.getByTestId("about-logs")).toBeEnabled();
  await second.evaluate(({ shell }) => {
    const opened: string[] = [];
    (globalThis as unknown as { opened: string[] }).opened = opened;
    shell.openPath = async (path: string) => { opened.push(path); return ""; };
  });
  await page.getByTestId("about-logs").click();
  const opened = await second.evaluate(() => (globalThis as unknown as { opened: string[] }).opened);
  assert.ok(opened.some(path => path.endsWith("logs")), `the log folder should open: ${opened.join(", ")}`);
  evidence["s5-logs"] = opened;
  await page.screenshot({ path: resolve(artifacts, "phase9-s5-about.png") });

  // S6: a real program renders, and a malformed one falls back without stopping the run.
  await home(page);
  await page.locator(".model-select select").selectOption("demo");
  await page.locator("#task").fill("demo render");
  await page.locator("button[type=submit]").click();
  await expect(page.getByTestId("ui-block")).toBeVisible({ timeout: 90000 });
  // The demo program is a Callout, a Table and a Tabs whose first panel holds another
  // Callout, so the callout count is two by design.
  await expect(page.getByTestId("ui-block").getByTestId("callout").first()).toBeVisible();
  assert.ok(await page.getByTestId("ui-block").getByTestId("callout").count() >= 2, "the tab panel renders too");
  await expect(page.getByTestId("ui-block").getByTestId("genui-table")).toBeVisible();
  await expect(page.getByTestId("ui-block").getByTestId("genui-tabs")).toBeVisible();
  evidence["s6-render"] = (await page.getByTestId("ui-block").innerText()).slice(0, 160);
  await page.screenshot({ path: resolve(artifacts, "phase9-s6-render.png") });
  await home(page);
  await page.locator("#task").fill("demo render bad");
  await page.locator("button[type=submit]").click();
  await expect(page.getByTestId("ui-fallback")).toBeVisible({ timeout: 90000 });
  await expect(page.getByTestId("ui-fallback")).toHaveAttribute("role", "status");
  await expect(page.locator(".stop")).toBeDisabled({ timeout: 30000 });
  evidence["s6-fallback"] = (await page.getByTestId("ui-fallback").innerText()).slice(0, 160);
  await page.screenshot({ path: resolve(artifacts, "phase9-s6-fallback.png") });
} finally {
  await second.close();
}

// ── S8: light, large and English at the reference size ───────────────────────────────────
const third = await launch("en");
try {
  const page = await ready(third);
  await page.locator(".settings").click();
  await page.locator(".settings-nav button").nth(1).click();
  await page.getByTestId("appearance-locale").getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.locator("html")).toHaveAttribute("data-font", "large");
  await home(page);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const overflow = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: innerWidth }));
  assert.ok(overflow.scroll <= overflow.width, `English overflows: ${overflow.scroll} > ${overflow.width}`);
  const body = await page.locator("body").boundingBox();
  const sidebar = await page.locator(".sidebar").boundingBox();
  assert.ok(body && sidebar && sidebar.x < body.width / 2, "in English the sidebar is on the left");
  const fontSize = await page.locator(".home-title").evaluate(element => getComputedStyle(element).fontSize);
  assert.ok(parseFloat(fontSize) > 32, `the large font should enlarge the title: ${fontSize}`);
  evidence["s8"] = { overflow, fontSize, dir: await page.evaluate(() => document.documentElement.dir) };
  await page.screenshot({ path: resolve(artifacts, "phase9-s8-english-light.png") });
} finally {
  await third.close();
}

console.log("Phase 9 walkthrough S1–S8 passed.");
console.log(JSON.stringify(evidence, null, 2));
