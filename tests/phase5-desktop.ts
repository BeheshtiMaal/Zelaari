/** Real Electron + offline engine/SQLite questions. No external provider or credentials. */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { _electron as electron, expect as baseExpect, type ElectronApplication, type Page } from "@playwright/test";
import type { QuestionRecord, WorkspaceState } from "../src/lib/protocol";
const expect = baseExpect.configure({ timeout: 30000 });
const profile = await mkdtemp(join(tmpdir(), "harness-phase5-profile-"));
const workspace = await mkdtemp(join(tmpdir(), "harness-phase5-project-"));
const second = await mkdtemp(join(tmpdir(), "harness-phase5-second-"));
const artifacts = resolve("artifacts/phase5"); await mkdir(artifacts, { recursive: true });
await writeFile(join(workspace, "README.md"), "# Question fixture\nbefore\n");
const errors: string[] = [], evidence: string[] = [];
async function api<T>(page: Page, path: string, method = "GET", body?: unknown): Promise<T> {
  return page.evaluate(async ({ path, method, body }) => {
    const bridge = window.harness!;
    const response = await fetch(bridge.baseUrl + path, { method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json();
  }, { path, method, body });
}
async function launch() {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  const app = await electron.launch({ args: [process.cwd()], env: { ...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
  const page = await app.firstWindow(); page.setDefaultTimeout(30000); await page.setViewportSize({ width: 1440, height: 900 });
  page.on("pageerror", error => errors.push(error.message));
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
  return { app, page };
}
const activeCard = (page: Page) => page.locator(".compose-region .question-card");
async function task(page: Page, text: string) {
  await page.locator(".sidebar nav button").first().click();
  await page.locator("#task").fill(text); await page.locator("button[type=submit]").click();
  await expect(activeCard(page)).toBeVisible();
}
async function done(page: Page) { await expect(activeCard(page)).toHaveCount(0); await expect(page.locator(".stop")).toBeDisabled(); }
async function openTask(page: Page, title: string) {
  const task = page.locator(".task-link").filter({ hasText: title });
  const group = page.locator(".workspace-history details").filter({ has: task });
  if (await group.getAttribute("open") === null) await group.locator("summary").click();
  await task.click();
}
function step(text: string) { evidence.push(text); console.log(`[phase5] ${text}`); }
let app: ElectronApplication | undefined, page: Page;
try {
  ({ app, page } = await launch());
  await api(page, "/settings", "PUT", { locale: "fa", default_model: "demo" });
  await api(page, "/workspaces", "POST", { path: workspace }); await page.reload();
  if (process.argv.includes("--other-inputs")) {
    await api(page, "/settings", "PUT", { locale: "en", default_model: "demo" }); await page.reload();
    step("multi Other-only, rank with additional Other, and fourth-key Other choice");
    for (const kind of ["multi", "rank", "exhausted"]) {
      await task(page, `demo question ${kind}`);
      const card = activeCard(page);
      if (kind === "exhausted") { await card.focus(); await card.press("4"); await expect(card.locator('input[type=text]')).toBeFocused(); }
      await card.locator('input[type=text]').fill(`Additional ${kind} preference`);
      if (kind === "multi") await expect(card.locator('input[type=checkbox]:checked')).toHaveCount(1);
      await card.focus(); await card.press("Enter"); await done(page);
      await expect(page.getByTestId("callout").last()).toContainText(`Additional ${kind} preference`);
    }
  } else {
  step("Persian dock, single keyboard choice, Other and request summary");
  await task(page, "demo question single");
  await expect(page.getByTestId("inbox-badge")).toHaveCount(0);
  await expect(page.getByTestId("current-waiting")).toContainText("۱");
  await expect(page.locator(".run-actions")).toContainText("منتظر پاسخ شما");
  // Phase 6 R13 fixes the Run information panel at 300px; the Phase 5 waiting count moved into it.
  assert.equal((await page.locator(".run-info").boundingBox())!.width, 300);
  let card = activeCard(page);
  await expect(card.locator(".question-footer")).toContainText("۱ تا ۳");
  assert.match(await card.ariaSnapshot(), /radio/);
  await card.focus(); await card.press("2");
  await expect(card.locator('input[type=radio]').nth(1)).toBeChecked();
  await card.press("3"); await expect(card.locator('input[type=text]')).toBeFocused();
  await card.locator('input[type=text]').fill("ترجیح من: تغییر کوچک");
  await card.locator('input[type=text]').press("Escape"); await expect(card).toBeVisible();
  await page.screenshot({ path: join(artifacts, "question-fa.png"), scale: "css" });
  await card.focus(); await card.press("Enter"); await done(page);
  await expect(page.locator(".question-history")).toContainText("پاسخ داده شد");

  step("English batch navigation, multi choices, rank move controls and drag");
  await api(page, "/settings", "PUT", { locale: "en", default_model: "demo" }); await page.reload();
  await task(page, "demo question batch"); card = activeCard(page);
  await card.focus(); await card.press("1"); await card.press("Enter");
  await expect(card.locator(".question-heading")).toContainText("Question 2 of 3");
  await card.focus(); await card.press("1"); await card.press("2");
  await card.getByRole("button", { name: "Back", exact: true }).click();
  await expect(card.locator('input[type=radio]').first()).toBeChecked();
  await card.getByRole("button", { name: "Next", exact: true }).click();
  await expect(card.locator('input[type=checkbox]:checked')).toHaveCount(2);
  await card.getByRole("button", { name: "Next", exact: true }).click();
  await card.focus(); await card.press("1");
  await expect(card.getByRole("button", { name: "Move down: Small focused change", exact: true })).toBeFocused();
  await card.getByRole("button", { name: "Move up: Refactor first", exact: true }).focus();
  await card.getByRole("button", { name: "Move up: Refactor first", exact: true }).press("Enter");
  await expect(card.locator(".question-rank").first()).toContainText("Refactor first");
  await card.locator('[data-rank="refactor"]').dragTo(card.locator('[data-rank="small"]'));
  await expect(card.locator(".question-rank").first()).toContainText("Small focused change");
  await page.screenshot({ path: join(artifacts, "rank-en.png"), scale: "css" });
  await card.getByRole("button", { name: "Send answer", exact: true }).click(); await done(page);

  step("validation, failed network submission, draft retention, IME and duplicate locking");
  await task(page, "demo question single"); card = activeCard(page);
  await card.getByRole("button", { name: "Send answer", exact: true }).click();
  await expect(card.getByRole("alert")).toBeVisible();
  await card.locator('input[type=text]').fill("Preserved answer");
  await card.locator('input[type=text]').dispatchEvent("keydown", { key: "Enter", code: "Enter", isComposing: true });
  await expect(card).toBeVisible();
  await page.route("**/runs/*/interrupts/*", route => route.fulfill({ status: 503, body: "Unavailable" }));
  await card.getByRole("button", { name: "Send answer", exact: true }).click();
  await expect(card.getByRole("alert")).toBeVisible();
  await expect(card.locator('input[type=text]')).toHaveValue("Preserved answer");
  await page.unroute("**/runs/*/interrupts/*");
  let posts = 0;
  await page.route("**/runs/*/interrupts/*", async route => { posts++; await new Promise(resolve => setTimeout(resolve, 100)); await route.continue(); });
  await card.locator(".question-send").evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await done(page); assert.equal(posts, 1); await page.unroute("**/runs/*/interrupts/*");

  step("mixed waiting, background workspace question and approval-only badge");
  await task(page, "demo question mixed"); card = activeCard(page);
  await expect(page.getByTestId("current-waiting")).toContainText("2");
  await expect(page.getByTestId("inbox-badge")).toHaveText("1");
  await api(page, "/workspaces", "POST", { path: second });
  const other = await api<{ run_id: string }>(page, "/runs", "POST", { task: "demo question rank background", workspace: second, model: "demo" });
  await expect.poll(async () => (await api<QuestionRecord[]>(page, `/runs/${other.run_id}/questions`)).length).toBe(1);
  await expect(page.locator(".task-dot.waiting")).toHaveCount(2);
  await card.getByRole("button", { name: "Decline", exact: true }).click();
  await expect(page.getByTestId("current-waiting")).toContainText("1");
  await expect(page.getByTestId("inbox-badge")).toHaveText("1");
  step("force-kill mid-barrier, reopen original run, resolve remaining approval once");
  const appProcess = app.process();
  const python = resolve("backend/.venv/Scripts/python.exe");
  const enginePid = Number(execFileSync(python, ["-c", "import psutil,sys; print(next(p.pid for p in psutil.Process(int(sys.argv[1])).children(recursive=True) if p.cmdline()[-2:] == ['-m','server']))", String(app.process().pid)], { encoding: "utf8", windowsHide: true }).trim());
  execFileSync(python, ["-c", "import psutil,sys; psutil.Process(int(sys.argv[1])).kill()", String(enginePid)], { windowsHide: true });
  await expect.poll(() => appProcess.exitCode).not.toBeNull();
  await app.close().catch(() => {}); ({ app, page } = await launch());
  await openTask(page, "demo question mixed");
  await expect(page.getByTestId("approval-card")).toBeVisible();
  await page.getByTestId("approval-approve").click(); await expect(page.locator(".stop")).toBeDisabled();
  // The approved effect is dispatched after the barrier releases, so the file lands asynchronously.
  await expect.poll(() => readFile(join(workspace, "demo-answer.txt"), "utf8").catch(() => "")).toBe("Approved mixed effect\n");
  await openTask(page, "background");
  await expect(activeCard(page)).toBeVisible(); await expect(page.getByTestId("inbox-badge")).toHaveCount(0);
  await expect(page.getByTestId("current-waiting")).toHaveText("1 item waiting for you");
  await page.screenshot({ path: join(artifacts, "question-en.png"), scale: "css" });
  await page.setViewportSize({ width: 800, height: 800 });
  await expect(page.locator(".run-layout")).toHaveCSS("flex-direction", "column");
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: join(artifacts, "question-narrow-en.png"), scale: "css" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator(".stop").click(); await done(page);

  step("grill picker, Home chip, two batches and graceful restart during interview");
  await api(page, "/workspaces", "POST", { path: workspace });
  await page.locator(".sidebar nav button").first().click();
  await page.locator("#task").fill("/gr"); await expect(page.getByRole("listbox")).toBeVisible();
  await page.locator("#task").press("ArrowDown"); await page.locator("#task").press("ArrowUp");
  await page.locator("#task").press("Enter");
  await expect(page.locator("#task")).toHaveValue("/grill "); await expect(page.locator(".run-header")).toHaveCount(0);
  await page.locator("#task").fill("/"); await page.locator("#task").press("Escape"); await expect(page.getByRole("listbox")).toHaveCount(0);
  await page.getByRole("button", { name: "Interview with grill-me", exact: true }).click(); await expect(page.locator("#task")).toHaveValue("/grill ");
  await page.locator("#task").fill("/grill improve parser"); await page.locator("button[type=submit]").click(); await expect(activeCard(page)).toBeVisible();
  await activeCard(page).locator('input[type=text]').fill("Only improve date parsing");
  await activeCard(page).getByRole("button", { name: "Send answer", exact: true }).click();
  await expect(activeCard(page).locator("legend")).toContainText("success");
  await app.close(); ({ app, page } = await launch());
  await openTask(page, "/grill improve parser");
  await expect(activeCard(page).locator("legend")).toContainText("success");
  await activeCard(page).locator('input[type=text]').fill("A focused regression test");
  await activeCard(page).getByRole("button", { name: "Send answer", exact: true }).click(); await done(page);
  await expect(page.getByTestId("callout").last()).toContainText("Interview complete");

  step("exhausted retry hint, change approach, stop/report, and card Esc decline");
  for (const choice of ["Retry with a hint", "Change approach", "Stop and report"]) {
    await task(page, "demo question exhausted"); card = activeCard(page);
    await card.getByText(choice, { exact: false }).first().click();
    if (choice === "Retry with a hint") await card.getByRole("textbox", { name: "Write your guidance" }).fill("Check the input format");
    await page.screenshot({ path: join(artifacts, `exhausted-${choice.split(" ")[0]}.png`), scale: "css" });
    await card.getByRole("button", { name: "Send answer", exact: true }).click(); await done(page);
  }
  await task(page, "demo question single"); await activeCard(page).focus(); await activeCard(page).press("Escape"); await done(page);
  await expect(page.locator(".question-history")).toContainText("Declined");
  }
  assert.deepEqual(errors, []);
  await writeFile(join(artifacts, process.argv.includes("--other-inputs") ? "other-inputs-evidence.json" : "evidence.json"), JSON.stringify({ passed: true, evidence, errors }, null, 2));
  step("passed");
} finally { await app?.close(); }
