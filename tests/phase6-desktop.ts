/** Real Electron, authenticated sidecar, SQLite and offline planning walkthrough. */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { _electron as electron, expect as baseExpect, type Page } from "@playwright/test";
import type { ApprovalRecord } from "../src/lib/protocol";
const expect = baseExpect.configure({ timeout: 45000 });
const artifacts = resolve("artifacts/phase6"); await mkdir(artifacts, { recursive: true });
const workspace = await mkdtemp(join(tmpdir(), "harness-phase6-project-"));
const profile = await mkdtemp(join(tmpdir(), "harness-phase6-profile-"));
await writeFile(join(workspace, "README.md"), "# Planning fixture\nRead this local context before reviewing.\n");
async function api<T>(page: Page, path: string, method = "GET", body?: unknown): Promise<T> {
  return page.evaluate(async ({ path, method, body }) => {
    const bridge = window.harness!;
    const response = await fetch(bridge.baseUrl + path, { method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json();
  }, { path, method, body });
}
const env: Record<string, string> = {};
for (const [key, value] of Object.entries(process.env)) if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
execFileSync(resolve("backend/.venv/Scripts/python.exe"), [resolve("backend/tests/phase6_seed.py"), profile, workspace], { env: { ...env, NODE_ENV: "production", PYTHONPATH: resolve("backend"), LANGSMITH_TRACING: "false", LANGCHAIN_TRACING_V2: "false" }, windowsHide: true, timeout: 90000 });
const app = await electron.launch({ args: [process.cwd()], env: { ...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
const page = await app.firstWindow(), errors: string[] = [], evidence: string[] = [];
page.on("pageerror", error => errors.push(error.message));
page.setDefaultTimeout(45000);
async function start(text: string) {
  await page.locator(".sidebar nav button").first().click();
  await page.locator("#task").fill(text); await page.locator("#task").press("Enter");
}
async function shot(name: string) { await page.screenshot({ path: join(artifacts, name + ".png"), scale: "css" }); }
try {
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
  const summaryTask = page.locator(".task-link").filter({ hasText: "Actual summary replay" });
  const history = page.locator(".workspace-history details").filter({ has: summaryTask });
  if (await history.getAttribute("open") === null) await history.locator("summary").click();
  await summaryTask.click();
  await expect(page.locator(".summary-notice")).toBeVisible();
  await shot("actual-summary-fa"); evidence.push("real installed summarizer notice and source survive Electron replay");
  await api(page, "/workspaces", "POST", { path: workspace });
  await api(page, "/settings", "PUT", { locale: "fa", default_model: "demo" }); await page.reload();
  await expect(page.locator("#task")).toBeEnabled();
  await start("demo planning large");
  await expect(page.getByTestId("approval-card")).toBeVisible();
  await expect(page.locator("#task")).toBeEnabled();
  await page.locator("#task").fill("Keep the public API unchanged"); await page.locator("#task").press("Enter");
  await expect(page.locator(".steering-status")).toContainText("در صف");
  await shot("plan-review-fa");
  await page.getByTestId("approval-approve").click();
  await expect(page.getByTestId("plan-checklist")).toBeVisible();
  await expect(page.getByTestId("approval-card")).toBeVisible();
  await expect(page.getByTestId("approval-card")).toContainText("notes.txt");
  await expect(page.locator(".delegate-card")).toHaveCount(2);
  await shot("run-fa");
  // A completed Thinking panel can be reopened and remains open while state updates.
  const completedStep = page.locator(".step-card").filter({ has: page.getByText("Read project context", { exact: true }) }).first();
  await completedStep.locator(":scope > button").focus();
  await completedStep.locator(":scope > button").press("Enter");
  await expect(completedStep.locator(":scope > button")).toHaveAttribute("aria-expanded", "true");
  const thinking = completedStep.locator(".thinking-panel").first();
  await thinking.locator(":scope > button").click();
  await expect(thinking.locator(".thinking-body")).toBeVisible();
  await page.getByTestId("approval-approve").click();
  await expect(page.locator(".stop")).toBeDisabled();
  await expect(thinking.locator(".thinking-body")).toBeVisible();
  assert.match(await readFile(join(workspace, "notes.txt"), "utf8"), /Reviewed local/);
  await expect(page.locator(".steering-status")).toContainText("تحویل داده شد");
  evidence.push("large reviewed plan, scoped reasoning, real read-only delegates, file approval and queued steering");
  await shot("finished-fa");
  await page.locator(".settings").click(); await page.locator(".settings-nav button").nth(2).click();
  await page.locator('.planning-settings input[type=number]').first().fill("5");
  await page.locator(".planning-settings form button").click();
  await expect(page.locator(".planning-settings .approval-card")).toBeVisible();
  await page.getByTestId("approval-approve").click();
  await expect(page.locator('.planning-settings input[type=number]').first()).toHaveValue("5");
  await page.locator('.planning-settings input[type=number]').nth(1).fill("6");
  await page.locator(".planning-settings form button").click();
  await page.getByTestId("approval-reject").click();
  await expect(page.locator('.planning-settings input[type=number]').nth(1)).toHaveValue("3");
  evidence.push("protected planning settings reviewed and saved");
  await page.locator(".settings-nav button").nth(1).click();
  await page.getByRole("button", { name: "English", exact: true }).click();
  await start("demo planning small");
  await expect(page.getByTestId("plan-checklist")).toBeVisible();
  await expect(page.locator(".stop")).toBeDisabled();
  await expect(page.getByTestId("plan-checklist")).toContainText("Automatically adopted");
  await shot("run-en");
  await page.setViewportSize({ width: 760, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await shot("run-en-narrow");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator(".workspace-toolbar select").last().selectOption("auto");
  await start("demo plan revisions");
  await expect(page.getByTestId("approval-card")).toContainText("s4");
  await page.getByTestId("approval-reject").click();
  await expect(page.getByTestId("approval-card")).toContainText("A step would be dropped");
  await page.getByTestId("approval-reject").click();
  await expect(page.locator(".stop")).toBeDisabled();
  await expect(page.locator(".plan-checklist li")).toHaveCount(4);
  evidence.push("Auto still reviews third cumulative addition and dropped steps; rejection preserves accepted scope");
  await page.locator(".settings").click(); await page.locator(".settings-nav button").nth(2).click();
  await page.locator('.planning-settings input[type=checkbox]').uncheck();
  await page.locator(".planning-settings form button").click(); await page.getByTestId("approval-approve").click();
  await start("demo plan revisions"); await expect(page.locator(".stop")).toBeDisabled();
  await expect(page.getByTestId("approval-card")).toHaveCount(0);
  await page.locator(".settings").click(); await page.locator(".settings-nav button").nth(2).click();
  await page.locator('.planning-settings input[type=checkbox]').check();
  await page.locator(".planning-settings form button").click(); await page.getByTestId("approval-approve").click();
  evidence.push("configuration rejection preserves values; deviation toggle saves require review even in Auto");
  await start("demo planning risky large outside");
  await expect(page.getByTestId("approval-card")).toContainText("outside.txt");
  await page.getByTestId("approval-approve").click();
  await expect(page.locator(".stop")).toBeDisabled();
  assert.match(await readFile(join(workspace, "outside.txt"), "utf8"), /Reviewed local/);
  evidence.push("Auto skips initial review but requires reviewed outside-scope mutation");
  await page.locator(".workspace-toolbar select").last().selectOption("ask");
  await start("demo planning risky small");
  await expect(page.getByTestId("approval-card")).toBeVisible();
  await page.getByTestId("approval-reject").click(); await expect(page.locator(".stop")).toBeDisabled();
  await expect(page.getByTestId("plan-checklist")).toHaveCount(0);
  await start("demo planning risky small");
  await expect(page.getByTestId("approval-card")).toBeVisible();
  await page.locator(".approval-actions button").nth(1).click();
  const planInput = page.locator('.approval-input textarea[dir=ltr]');
  const editedPlan = JSON.parse(await planInput.inputValue()) as { steps: { title: string }[] };
  editedPlan.steps[0].title = "Human reviewed project context";
  await planInput.fill(JSON.stringify(editedPlan)); await page.locator(".approval-actions .approve").click();
  await expect(page.getByTestId("approval-card")).toContainText("Human reviewed project context");
  await page.getByTestId("approval-approve").click(); await expect(page.locator(".stop")).toBeDisabled();
  evidence.push("high-risk small plans require review; rejection and edited-plan preview work");
  await start("demo planning small forbidden"); await expect(page.locator(".stop")).toBeDisabled();
  const reviewStep = page.locator(".step-card").filter({ has: page.getByText("Review local source", { exact: true }) }).first();
  await reviewStep.locator(":scope > button").click();
  await expect(reviewStep.locator(".delegate-card")).toHaveCount(2);
  for (const child of await reviewStep.locator(".delegate-card").all()) {
    await child.locator(":scope > button").click(); await expect(child).toContainText("Permission denied");
  }
  await assert.rejects(readFile(join(workspace, "forbidden.txt")));
  await shot("read-only-denial-en"); evidence.push("real child write/command denials remain read-only and visible");
  await start("demo question single");
  await expect(page.locator(".compose-region .question-card")).toBeVisible();
  await page.locator("#task").fill("Preserve this draft");
  let attemptedMessages = 0;
  await page.route("**/runs/*/messages", route => { attemptedMessages++; return route.fulfill({ status: 503, contentType: "application/json", body: "{}" }); });
  await page.locator("#task").dispatchEvent("keydown", { key: "Enter", isComposing: true });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(attemptedMessages, 0);
  await page.locator("#task").press("Enter"); await expect(page.locator("#task")).toHaveValue("Preserve this draft");
  await expect(page.locator(".compose-region p[role=alert]")).toContainText("draft");
  await page.unroute("**/runs/*/messages");
  await page.locator("#task").press("Shift+Enter"); await expect(page.locator("#task")).toHaveValue("Preserve this draft\n");
  await page.locator(".stop").evaluate(element => {
    const button = element as HTMLButtonElement;
    button.addEventListener("click", () => {
      const start = performance.now();
      const observer = new MutationObserver(() => {
        if (button.disabled) { button.dataset.stopElapsed = String(performance.now() - start); observer.disconnect(); }
      });
      observer.observe(button, { attributes: true, attributeFilter: ["disabled"] });
    }, { once: true });
  });
  await page.locator(".stop").click(); await expect(page.locator(".stop")).toBeDisabled();
  const elapsed = Number(await page.locator(".stop").getAttribute("data-stop-elapsed"));
  assert.ok(elapsed > 0 && elapsed < 1000, `Stop event to terminal UI: ${elapsed} ms`);
  evidence.push(`failed steering retains draft; Shift+Enter adds newline; Stop event to terminal UI ${elapsed.toFixed(0)} ms`);
  await start("demo question single"); await expect(page.locator(".compose-region .question-card")).toBeVisible();
  await page.locator(".composer .send").click(); await expect(page.locator(".stop")).toBeDisabled();
  evidence.push("composer Stop, keyboard expansion, ARIA, IME isolation and reduced-motion layout");
  const pending = await api<ApprovalRecord[]>(page, "/approvals?status=pending"); assert.equal(pending.length, 0);
  assert.deepEqual(errors, []);
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({ passed: true, evidence, errors }, null, 2));
  console.log("Phase 6 Electron walkthrough passed", evidence);
} catch (error) { await shot("failure"); throw error; }
finally { await app.close(); }
