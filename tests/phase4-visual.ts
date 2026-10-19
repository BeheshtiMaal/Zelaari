/** Reference-size visual checks with real pending built-in demo approvals. */
import assert from "node:assert/strict";
import { readdir, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { _electron as electron, expect as baseExpect, type Page } from "@playwright/test";
const expect = baseExpect.configure({ timeout: 30000 });
const profiles = await Promise.all((await readdir(tmpdir())).filter(name => name.startsWith("harness-phase4-profile-")).map(async name => ({ path: join(tmpdir(), name), time: (await stat(join(tmpdir(), name))).mtimeMs })));
profiles.sort((a, b) => b.time - a.time); assert.ok(profiles.length);
const env: Record<string, string> = {};
for (const [key, value] of Object.entries(process.env)) if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
const app = await electron.launch({ args: [process.cwd()], env: { ...env, CODEHARNESS_TEST_USER_DATA: profiles[0].path, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
async function api<T>(page: Page, path: string, method = "GET", value?: unknown): Promise<T> {
  return page.evaluate(async ({ path, method, value }) => {
    const bridge = window.harness!;
    const result = await fetch(bridge.baseUrl + path, { method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" }, ...(value === undefined ? {} : { body: JSON.stringify(value) }) });
    if (!result.ok) throw new Error(`HTTP ${result.status}`); return result.json();
  }, { path, method, value });
}
const runs: string[] = [];
try {
  const page = await app.firstWindow(); await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
  // Repeated visual runs reuse only the disposable test profile. Clear prior
  // unfinished visual fixtures, while retaining history for real UI coverage.
  const previous = await api<{ status: string; request: { run_id: string; args: Record<string, unknown> } }[]>(page, "/approvals");
  for (const run of new Set(previous.filter(record => record.status === "pending" && JSON.stringify(record.request.args).includes("visual-")).map(record => record.request.run_id))) await api(page, `/runs/${run}/stop`, "POST");
  const state = await api<{ selected: string }>(page, "/workspaces"); assert.ok(state.selected);
  for (const name of ["visual-a.py", "visual-b.py"]) {
    await writeFile(join(state.selected, name), "def parse_date(s):\n    return s\n");
    const run = await api<{ run_id: string }>(page, "/runs", "POST", { task: `demo edit ${name}: return s => return s.strip()`, workspace: state.selected, model: "demo", mode: "ask" }); runs.push(run.run_id);
  }
  await api(page, "/settings", "PUT", { locale: "fa", default_model: "demo" });
  await page.goto("app://codeharness/approvals/");
  await expect(page.getByTestId("inbox-badge")).toHaveText("۲");
  await page.locator(".inbox-row:not(.decided)").filter({ hasText: "visual-a.py" }).click();
  await expect(page.locator(".inbox-row.selected")).toHaveCSS("background-color", "rgb(23, 42, 45)");
  assert.equal((await page.locator(".inbox-list").boundingBox())!.width, 360);
  assert.equal((await page.locator(".sidebar").boundingBox())!.width, 240);
  await expect(page.locator(".diff-line.remove").first()).toHaveCSS("background-color", "rgb(58, 26, 26)");
  await expect(page.locator(".diff-line.add").first()).toHaveCSS("background-color", "rgb(18, 48, 31)");
  await page.screenshot({ path: resolve("artifacts/phase4/reference-inbox-fa.png"), scale: "css" });
  await api(page, "/settings", "PUT", { locale: "en", default_model: "demo" });
  await page.reload(); await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await page.locator(".inbox-row:not(.decided)").filter({ hasText: "visual-a.py" }).click();
  await page.screenshot({ path: resolve("artifacts/phase4/reference-inbox-en.png"), scale: "css" });
  await page.setViewportSize({ width: 1000, height: 800 });
  await expect(page.locator(".inbox-panes")).toHaveCSS("flex-direction", "column");
  await page.screenshot({ path: resolve("artifacts/phase4/reference-inbox-narrow-en.png"), scale: "css" });
  for (const run of runs) await api(page, `/runs/${run}/stop`, "POST");
  console.log("[phase4-visual] real approvals at 1440x900 in both directions; 360px list, 240px sidebar and narrow stacking passed");
} finally { await app.close(); }
