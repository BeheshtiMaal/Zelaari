/** Real Windows Electron, vault, HTTP engine, graph and filesystem; only provider is scripted. */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, mkdir, readFile, writeFile, stat, rename } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { _electron as electron, expect as baseExpect, type ElectronApplication, type Page } from "@playwright/test";
const expect = baseExpect.configure({ timeout: 30000 });
import type { ApprovalRecord } from "../src/lib/protocol";
import { approvalCopy } from "../src/i18n/approvals";

const artifacts = resolve("artifacts/phase4");
await mkdir(artifacts, { recursive: true });
const profile = await mkdtemp(join(tmpdir(), "harness-phase4-profile-"));
const workspace = await mkdtemp(join(tmpdir(), "harness-phase4-project-"));
const secondWorkspace = await mkdtemp(join(tmpdir(), "harness-phase4-second-"));
await mkdir(join(secondWorkspace, "src"));
await mkdir(join(workspace, "src"));
await writeFile(join(workspace, "src/parser.py"), "def parse_date(s):\r\n    return s\r\n");
await writeFile(join(workspace, "src/demo.txt"), "before");
const original = await readFile(join(workspace, "src/parser.py"));
const results: string[] = [], errors: string[] = [];
const fixtureKey = "synthetic-phase4-vault-canary";
const server = createServer(async (request, response) => {
  if (request.url === "/v1/models") { response.writeHead(200, { "Content-Type": "application/json" }); response.end(JSON.stringify({ data: [{ id: "fixture", context_window: 65536 }] })); return; }
  let body = ""; for await (const chunk of request) body += String(chunk);
  const input = JSON.parse(body) as { stream?: boolean; tools?: { function: { name: string } }[]; messages: { role: string; content: string }[] };
  const probe = input.tools?.some(tool => tool.function.name === "harness_probe");
  const task = input.messages.find(message => message.role === "user")?.content ?? "";
  const answered = input.messages.some(message => message.role === "tool");
  if (answered) results.push(input.messages.filter(message => message.role === "tool").map(message => message.content).join("\n"));
  let calls = task.includes("pair") ? [
    { name: "edit_file", args: { file_path: "src/parser.py", old_string: "return s", new_string: "return s.strip()" }, id: "edit-one" },
    { name: "write_file", args: { file_path: "src/rejected.py", content: "should not exist" }, id: "write-two" },
  ] : [{ name: "write_file", args: { file_path: `src/${task.includes("second") ? "second" : "restart"}.txt`, content: "restart survived" }, id: "restart-write" }];
  if (task.includes("command")) calls = [{ name: "run_command", args: { command: "Add-Content launches.txt launch; Start-Sleep -Seconds 45", timeout: 60 }, id: "crash-command" }] as unknown as typeof calls;
  if (probe) calls = [{ name: "harness_probe", args: { marker: "connection-ok" }, id: "probe" }] as unknown as typeof calls;
  if (answered) calls = [];
  const content = calls.length ? "" : 'root = Callout("done");';
  const tool_calls = calls.map(call => ({ id: call.id, type: "function", function: { name: call.name, arguments: JSON.stringify(call.args) } }));
  response.writeHead(200, { "Content-Type": input.stream ? "text/event-stream" : "application/json" });
  if (input.stream) {
    response.write(`data: ${JSON.stringify({ id: "fixture", object: "chat.completion.chunk", choices: [{ index: 0, delta: { role: "assistant", content, ...(calls.length ? { tool_calls: tool_calls.map((call, index) => ({ ...call, index })) } : {}) }, finish_reason: null }] })}\n\n`);
    response.write(`data: ${JSON.stringify({ id: "fixture", object: "chat.completion.chunk", choices: [{ index: 0, delta: {}, finish_reason: calls.length ? "tool_calls" : "stop" }], usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } })}\n\n`);
    response.end("data: [DONE]\n\n");
  } else response.end(JSON.stringify({ id: "fixture", model: "fixture", choices: [{ index: 0, message: { role: "assistant", content, ...(calls.length ? { tool_calls } : {}) }, finish_reason: calls.length ? "tool_calls" : "stop" }], usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } }));
});
await new Promise<void>(accept => server.listen(0, "127.0.0.1", accept));
const address = server.address(); assert.ok(address && typeof address === "object");
const base = `http://127.0.0.1:${address.port}/v1`;
function step(text: string) { console.log(`[phase4] ${text}`); }
async function launch() {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  const app = await electron.launch({ args: [process.cwd()], env: { ...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
  const page = await app.firstWindow(); page.setDefaultTimeout(25000);
  page.on("pageerror", error => errors.push(error.message));
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
  return { app, page };
}
async function api<T>(page: Page, path: string, method = "GET", value?: unknown): Promise<T> {
  return page.evaluate(async ({ path, method, value }) => {
    const bridge = window.harness!;
    const result = await fetch(bridge.baseUrl + path, { method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" }, ...(value === undefined ? {} : { body: JSON.stringify(value) }) });
    if (!result.ok) throw new Error(`HTTP ${result.status}`);
    return result.json();
  }, { path, method, value }) as Promise<T>;
}
async function exists(path: string) { try { await stat(path); return true; } catch { return false; } }
async function task(page: Page, text: string) {
  await page.locator(".sidebar nav button").first().click();
  await page.locator("#task").fill(text); await page.locator("button[type=submit]").click();
  await expect(page.getByTestId("approval-card").first()).toBeVisible({ timeout: 60000 });
}
async function inbox(page: Page) {
  await page.locator('a[href="/approvals/"]').first().click();
  await expect(page.locator(".inbox-screen")).toBeVisible();
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
}
async function crashEngine(app: ElectronApplication) {
  const appProcess = app.process(), pid = appProcess.pid!;
  const python = resolve("backend/.venv/Scripts/python.exe");
  const enginePid = Number(execFileSync(python, ["-c", "import psutil,sys; print(next(p.pid for p in psutil.Process(int(sys.argv[1])).children(recursive=True) if p.cmdline()[-2:] == ['-m','server']))", String(pid)], { encoding: "utf8", windowsHide: true }).trim());
  execFileSync(python, ["-c", "import psutil,sys; psutil.Process(int(sys.argv[1])).kill()", String(enginePid)], { windowsHide: true });
  await expect.poll(() => appProcess.exitCode, { timeout: 20000 }).not.toBeNull();
}
let app: ElectronApplication | undefined, page: Page;
try {
  step("launch and configure fixture through vault");
  ({ app, page } = await launch());
  assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
  const saved = await page.evaluate(async ({ base, key }) => window.harness!.saveModel({ id: "phase4-fixture", name: "Fixture", base_url: base, model: "fixture", api_key: key }), { base, key: fixtureKey });
  assert.ok(saved.ok);
  await api(page, "/models/phase4-fixture/test", "POST");
  await api(page, "/settings", "PUT", { locale: "fa", default_model: "phase4-fixture" });
  await api(page, "/workspaces", "POST", { path: workspace });
  await page.reload(); await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true");
  step("built-in offline demo edit approval");
  await page.locator(".model-select select").selectOption("demo");
  await task(page, "demo edit src/demo.txt: before => after");
  await page.getByTestId("approval-card").getByRole("button", { name: approvalCopy("fa").collapse, exact: true }).click();
  await expect(page.getByRole("button", { name: approvalCopy("fa").reviewOpen, exact: true })).toBeVisible();
  await page.screenshot({ path: join(artifacts, "inline-compact-fa.png") });
  await page.getByRole("button", { name: approvalCopy("fa").reviewOpen, exact: true }).click();
  await page.getByTestId("approval-approve").click();
  await expect.poll(() => readFile(join(workspace, "src/demo.txt"), "utf8")).toBe("after");
  await page.locator(".sidebar nav button").first().click();
  await page.locator(".model-select select").selectOption("phase4-fixture");
  step("parallel approvals, edit preview and keyboard safety");
  await task(page, "pair approval fixture");
  await expect(page.getByTestId("approval-card")).toHaveCount(2);
  await expect(page.getByTestId("inbox-badge")).toHaveText("۲");
  await page.screenshot({ path: join(artifacts, "inline-fa.png") });
  await inbox(page);
  await page.locator(".inbox-row").filter({ hasText: "src/parser.py" }).click();
  let card = page.locator(".inbox-detail .approval-card");
  await expect(card.getByTestId("diff-view")).toContainText("+    return s.strip()");
  await page.screenshot({ path: join(artifacts, "inbox-fa.png") });
  await card.getByRole("button", { name: approvalCopy("fa").edit, exact: true }).click();
  const input = card.locator('textarea[dir="ltr"]');
  await input.fill(JSON.stringify({ file_path: "src/parser.py", old_string: "return s", new_string: "return s.strip().replace('/', '-')" }));
  await input.press("Enter"); assert.deepEqual(await readFile(join(workspace, "src/parser.py")), original);
  await card.getByRole("button", { name: approvalCopy("fa").review, exact: true }).click();
  await expect(card.getByTestId("diff-view")).toContainText("replace");
  await card.locator('input[type="checkbox"]').check();
  await card.getByTestId("approval-approve").click();
  await expect(page.locator(".inbox-row").filter({ hasText: "src/rejected.py" })).toBeVisible();
  assert.deepEqual(await readFile(join(workspace, "src/parser.py")), original);
  await page.locator(".inbox-row").filter({ hasText: "src/rejected.py" }).click();
  await card.locator("textarea").fill("Choose a safer approach");
  await card.locator("textarea").press("Escape");
  await expect(card.getByTestId("approval-reject")).toBeVisible();
  await card.focus(); await page.keyboard.press("Escape");
  await expect.poll(() => readFile(join(workspace, "src/parser.py"), "utf8")).toContain("replace");
  assert.equal(await exists(join(workspace, "src/rejected.py")), false);
  await expect.poll(() => results.some(result => result.includes("Choose a safer approach"))).toBe(true);
  step("linked rule proposal and inbox history");
  await page.locator(".inbox-row").filter({ hasText: approvalCopy("fa").rules }).first().click();
  await expect(card.getByTestId("diff-view")).toContainText("src/**");
  assert.equal(await exists(join(workspace, ".harness/rules.json")), false);
  await card.getByTestId("approval-approve").click();
  await expect(page.getByTestId("inbox-badge")).toHaveCount(0);
  assert.ok((await readFile(join(workspace, ".harness/rules.json"), "utf8")).includes("src/**"));
  await page.getByRole("tab", { name: approvalCopy("fa").approved, exact: true }).click();
  await expect(page.locator(".inbox-row")).toHaveCount(3);
  await page.getByRole("tab", { name: approvalCopy("fa").rejected, exact: true }).click();
  await expect(page.locator(".inbox-row")).toHaveCount(1);
  await page.screenshot({ path: join(artifacts, "history-fa.png") });
  step("Rules grid chrome and explicit save approval");
  await page.locator('a[href="/customize/"]').click();
  await expect(page.locator(".rules-panel").first()).toBeVisible();
  await page.getByRole("button", { name: approvalCopy("fa").add, exact: true }).click();
  await page.locator(".rules-table input").nth(2).fill("delete");
  await page.locator(".rules-table input").nth(3).fill("build/**");
  await page.locator(".rules-table select").last().selectOption("deny");
  await page.screenshot({ path: join(artifacts, "rules-fa.png") });
  await page.getByRole("button", { name: approvalCopy("fa").save, exact: true }).click();
  await expect(page.locator(".rules-panel [role=status]")).toBeVisible();
  await inbox(page); await card.getByTestId("approval-reject").click();
  assert.equal((await readFile(join(workspace, ".harness/rules.json"), "utf8")).includes("build/**"), false);
  step("background tasks and graceful app restart");
  await page.goto("app://codeharness/"); await task(page, "restart first fixture");
  await api(page, "/workspaces", "POST", { path: secondWorkspace });
  await page.goto("app://codeharness/");
  await task(page, "restart second fixture");
  await expect(page.getByTestId("inbox-badge")).toHaveText("۲");
  await expect(page.locator(".task-dot.waiting")).toHaveCount(2);
  step("force-kill while approvals wait; missing vault credential keeps them pending");
  await crashEngine(app);
  await writeFile(join(profile, "vault.json"), "{}");
  ({ app, page } = await launch());
  card = page.locator(".inbox-detail .approval-card");
  await inbox(page); await expect(page.getByTestId("inbox-badge")).toHaveText("۲", { timeout: 30000 });
  await card.getByTestId("approval-approve").click();
  await expect(card.locator("[role=alert]")).toBeVisible();
  assert.equal((await api<ApprovalRecord[]>(page, "/approvals?status=pending")).length, 2);
  assert.ok((await page.evaluate(async ({ base, key }) => window.harness!.saveModel({ id: "phase4-fixture", name: "Fixture", base_url: base, model: "fixture", api_key: key }), { base, key: fixtureKey })).ok);
  await app.close(); ({ app, page } = await launch());
  card = page.locator(".inbox-detail .approval-card");
  await inbox(page); await expect(page.getByTestId("inbox-badge")).toHaveText("۲");
  for (let index = 0; index < 2; index++) { await card.getByTestId("approval-approve").click(); await expect.poll(async () => (await api<ApprovalRecord[]>(page, "/approvals?status=pending")).length).toBe(1 - index); }
  await expect.poll(() => exists(join(workspace, "src/restart.txt"))).toBe(true);
  await expect.poll(() => exists(join(secondWorkspace, "src/second.txt"))).toBe(true);
  step("temporarily unavailable workspace stays in history and can be restored");
  await expect.poll(async () => (await api<{ tasks: { workspace: string; status: string }[] }>(page, "/workspaces")).tasks.filter(task => task.workspace === secondWorkspace).every(task => task.status === "completed")).toBe(true);
  await rename(secondWorkspace, secondWorkspace + "-offline");
  await page.goto("app://codeharness/");
  await page.locator(".workspace-picker select").selectOption(secondWorkspace);
  await expect(page.locator(".compose-region [role=alert]")).toBeVisible();
  await rename(secondWorkspace + "-offline", secondWorkspace);
  step("force-kill engine during a command, then inspect recovery");
  await api(page, "/workspaces", "POST", { path: workspace });
  await page.goto("app://codeharness/"); await task(page, "command crash fixture");
  await page.getByTestId("approval-approve").click();
  await expect.poll(() => exists(join(workspace, "launches.txt"))).toBe(true);
  await crashEngine(app);
  ({ app, page } = await launch());
  card = page.locator(".inbox-detail .approval-card");
  await inbox(page); await expect.poll(async () => (await api<ApprovalRecord[]>(page, "/approvals")).filter(record => record.status === "pending").length).toBe(0);
  const tasks = await api<{ tasks: { id: string; title: string }[] }>(page, "/workspaces");
  const interrupted = tasks.tasks.find(task => task.title.includes("command crash"))!;
  await page.locator(".task-link").filter({ hasText: "command crash" }).click();
  await expect(page.getByTestId("interrupted-card")).toBeVisible({ timeout: 30000 });
  assert.deepEqual((await readFile(join(workspace, "launches.txt"), "utf8")).trim().split(/\r?\n/), ["launch"]);
  assert.ok(interrupted.id);
  await page.screenshot({ path: join(artifacts, "interrupted-fa.png") });
  step("explicit retry gets fresh review and edited arguments");
  await page.getByTestId("interrupted-card").getByRole("button", { name: approvalCopy("fa").retry, exact: true }).click();
  await expect(card).toContainText("300s");
  await card.getByRole("button", { name: approvalCopy("fa").edit, exact: true }).click();
  await card.locator('textarea[dir="ltr"]').fill(JSON.stringify({ command: "Add-Content launches.txt retry", timeout: 300, mode: "ask" }));
  await card.getByRole("button", { name: approvalCopy("fa").review, exact: true }).click();
  await card.getByTestId("approval-approve").click();
  await expect.poll(async () => (await readFile(join(workspace, "launches.txt"), "utf8")).trim().split(/\r?\n/)).toEqual(["launch", "retry"]);
  step("remembered English and responsive inbox");
  await api(page, "/settings", "PUT", { locale: "en", default_model: "phase4-fixture" });
  await page.goto("app://codeharness/approvals/"); await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await page.getByRole("tab", { name: "All", exact: true }).click();
  await page.screenshot({ path: join(artifacts, "inbox-en.png") });
  await page.setViewportSize({ width: 1000, height: 800 });
  await expect(page.locator(".inbox-panes")).toHaveCSS("flex-direction", "column");
  await page.screenshot({ path: join(artifacts, "inbox-narrow-en.png") });
  assert.deepEqual(errors, []);
  const logs = await readFile(join(profile, "catalog.json"), "utf8");
  assert.equal(logs.includes(fixtureKey), false);
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({ passed: true, scenarios: ["parallel", "edit", "reject", "allow-rule", "rules-grid", "background", "restart", "force-kill-command", "fa-en", "responsive"], rendererErrors: errors }, null, 2));
  step("desktop validation passed");
} finally { await app?.close().catch(() => undefined); server.close(); }
