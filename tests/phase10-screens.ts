/**
 * The README screenshots: the packaged app, Persian, at the reference size.
 *
 * Every image in `docs/screenshots/` comes from this file. It launches
 * `dist/win-unpacked/CodeHarness.exe` — the tree the installer lays down — and drives the
 * real screens. Most use the built-in demo model with no key and no network. Two need state
 * a person cannot conjure on demand: the pending approval is a real demo run whose plan was
 * accepted and whose edit is left waiting, and the jail refusal comes from a local
 * OpenAI-compatible server that asks for a path outside the workspace. In both cases the
 * engine, the tools, the permission layer and the cards are real; only the model is scripted.
 *
 * Run: npx tsx tests/phase10-screens.ts
 *
 * If the environment injects `NODE_OPTIONS` with a safe-delete shim (some sandboxes do), run
 * it as `env -u NODE_OPTIONS npx tsx tests/phase10-screens.ts`: the shim refuses the bulk
 * delete of the disposable profile and fails Playwright's own teardown.
 */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { _electron as electron, expect as baseExpect, type ElectronApplication, type Page } from "@playwright/test";

// Matchers carry their own timeout; a packaged first run can take a minute to warm up.
const expect = baseExpect.configure({ timeout: 90000 });

const root = process.cwd();
const output = resolve(root, "docs/screenshots");
await mkdir(output, { recursive: true });
// A disposable profile under the ignored `artifacts/`, so the workspace path printed in the
// screenshots reads like a project folder rather than a random temp directory.
const profile = resolve(root, "artifacts/readme-profile");
await rm(profile, { recursive: true, force: true });
await mkdir(profile, { recursive: true });
const executable = resolve(root, "dist/win-unpacked/CodeHarness.exe");
const forbidden = "C:\\Users\\sam\\.ssh\\id_rsa";

// -- a deterministic provider, so a pending approval and a jail refusal exist on cue -------
const server = createServer(async (request, response) => {
  if (request.url === "/v1/models") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ data: [{ id: "local", context_window: 65536 }] }));
    return;
  }
  let body = "";
  for await (const part of request) body += String(part);
  const input = JSON.parse(body) as { model: string; stream?: boolean; tools?: { function: { name: string } }[]; messages: { role: string; content: string }[] };
  const task = input.messages.find(message => message.role === "user")?.content ?? "";
  const answered = input.messages.some(message => message.role === "tool");
  // The connection test binds one tool and checks the answer calls it; without this the
  // model would be saved as "no tools" and the engine would refuse to start a run on it.
  const probe = input.tools?.some(tool => tool.function.name === "harness_probe") ?? false;
  let call: { name: string; arguments: string } | undefined;
  if (probe) call = { name: "harness_probe", arguments: JSON.stringify({ marker: "connection-ok" }) };
  else if (!answered) {
    if (task.includes("jail")) call = { name: "read_file", arguments: JSON.stringify({ file_path: forbidden }) };
    else if (task.includes("edit")) call = { name: "edit_file", arguments: JSON.stringify({ file_path: "src/app.py", old_string: "return s", new_string: "return s.strip()" }) };
    else call = { name: "read_file", arguments: JSON.stringify({ file_path: "README.md" }) };
  }
  const content = call ? "" : 'root = Callout("done");';
  const tools = call ? [{ id: `call-${Date.now()}`, type: "function", function: call }] : undefined;
  response.writeHead(200, { "Content-Type": input.stream ? "text/event-stream" : "application/json" });
  if (input.stream) {
    const chunk = (delta: unknown, finish: string | null = null) => ({ id: "local", object: "chat.completion.chunk", model: input.model, choices: [{ index: 0, delta, finish_reason: finish }] });
    for (const packet of [
      chunk({ role: "assistant" }),
      chunk({ content, ...(tools ? { tool_calls: tools.map((tool, index) => ({ ...tool, index })) } : {}) }),
      chunk({}, call ? "tool_calls" : "stop"),
      { id: "local", model: input.model, choices: [], usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } },
    ]) response.write(`data: ${JSON.stringify(packet)}\n\n`);
    response.end("data: [DONE]\n\n");
  } else {
    response.end(JSON.stringify({ id: "local", type: "chat.completion", model: input.model, choices: [{ index: 0, message: { role: "assistant", content, tool_calls: tools }, finish_reason: call ? "tool_calls" : "stop" }], usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } }));
  }
});
await new Promise<void>(accept => server.listen(0, "127.0.0.1", accept));
const address = server.address();
assert.ok(address && typeof address === "object");
const base = `http://127.0.0.1:${address.port}/v1`;

// -- launch --------------------------------------------------------------------------------
async function launch(): Promise<ElectronApplication> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    // The sandbox routes loopback through a proxy; a local provider must not go through it.
    if (!value || key.endsWith("_PROXY") || key.endsWith("_proxy") || key === "ELECTRON_RUN_AS_NODE" || key.endsWith("API_KEY") || key.startsWith("LANGSMITH_") || key.startsWith("LANGCHAIN_")) continue;
    env[key] = value;
  }
  return electron.launch({ executablePath: executable, args: [], env: { ...env, NO_PROXY: "127.0.0.1,localhost", CODEHARNESS_LANGUAGE: "fa", CODEHARNESS_TEST_USER_DATA: profile }, timeout: 180000 });
}

async function api<T>(page: Page, path: string, method = "GET", value?: unknown): Promise<T> {
  return page.evaluate(async ({ path, method, value }) => {
    const bridge = window.harness!;
    const result = await fetch(bridge.baseUrl + path, { method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" }, ...(value === undefined ? {} : { body: JSON.stringify(value) }) });
    if (!result.ok) throw new Error(`HTTP ${result.status} ${path}`);
    return result.json();
  }, { path, method, value });
}

const app = await launch();
const captured: string[] = [];
process.on("unhandledRejection", reason => console.error("[screens] unhandled rejection:", reason));
process.on("uncaughtException", error => console.error("[screens] uncaught:", error));
try {
  const page = await app.firstWindow();
  page.setDefaultTimeout(90000);
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 180000 });
  await page.setViewportSize({ width: 1440, height: 900 });
  assert.equal(await page.evaluate(() => document.documentElement.dir), "rtl");

  async function shot(name: string): Promise<void> {
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(350);
    const path = resolve(output, `${name}.png`);
    // `device` keeps the full pixel grid: this display runs at 133%, so a 1080x675 CSS
    // viewport is exactly the 1440x900 reference image the mocks were drawn at.
    await page.screenshot({ path, scale: "device" });
    captured.push(name);
    console.log(`[screens] ${name}.png`);
  }

  // 1. Home: the first run, before a folder and a model are chosen.
  await expect(page.getByTestId("state-no-workspace")).toBeVisible();
  await shot("home");

  // 2. Main: the sample project open and the demo model selected, ready to type.
  await page.getByTestId("state-sample-project").click();
  await expect(page.getByTestId("state-no-workspace")).toHaveCount(0);
  await page.locator(".model-select select").selectOption("demo");
  const workspace = resolve(profile, "sample-project");
  await mkdir(resolve(workspace, "src"), { recursive: true });
  await writeFile(resolve(workspace, "src", "app.py"), "def parse(value):\n    return s\n");
  await expect(page.getByTestId("state-no-model")).toHaveCount(0);
  await shot("main");

  // 3. Run: a real demo run that reads the sample's README.
  await page.locator("#task").fill("read README.md and summarize");
  const created = page.waitForResponse(response => new URL(response.url()).pathname === "/runs" && response.request().method() === "POST");
  await page.locator("button[type=submit]").click();
  const runId = ((await (await created).json()) as { run_id: string }).run_id;
  await expect(page.getByTestId("tool-line")).toBeVisible();
  await expect(page.locator(".stop")).toBeDisabled({ timeout: 90000 });
  await shot("run");

  // 4. Workspace: the file browser, with the sample's README open.
  await page.goto(`app://codeharness/workspaces/?path=${encodeURIComponent(workspace)}`);
  await expect(page.locator(".ws-row").filter({ hasText: "README.md" })).toBeVisible();
  await page.locator(".ws-row").filter({ hasText: "README.md" }).first().click();
  await expect(page.locator(".ws-code")).toBeVisible();
  await shot("workspace");

  // 5. Skills: the customize screen. The sample's project skill ships switched off on
  //    purpose, so the screen shows its nudge and a count that says so: one skill, none on.
  await page.goto("app://codeharness/customize/");
  await expect(page.getByTestId("customize-tab-skills")).toBeVisible();
  await expect(page.getByTestId("customize-counts")).toContainText("۰");
  await shot("skills");

  // 6. Schedule: a real schedule. The dependency-review template fills the dialog through
  //    the app's own handlers — weekly, 09:00, read-only with a report — so the saved row
  //    carries exactly what the dialog shows.
  await page.goto("app://codeharness/schedule/");
  await expect(page.getByTestId("schedule-screen")).toBeVisible();
  await page.getByTestId("schedule-template-dependencies").click();
  await expect(page.getByTestId("schedule-dialog")).toBeVisible();
  await expect(page.getByTestId("schedule-time")).toHaveValue("09:00");
  await shot("schedule-add");
  await page.getByTestId("schedule-confirm").click();
  await expect(page.getByTestId("schedule-dialog")).toBeHidden({ timeout: 30000 });
  await expect(page.locator("[data-testid^=schedule-row-]")).toHaveCount(1);
  await shot("schedule");

  // 7. Empty: the approvals inbox with nothing waiting. With no records at all the screen
  //    shows its empty state instead of the two panes.
  await page.goto("app://codeharness/approvals/");
  await expect(page.getByTestId("state-empty-inbox")).toBeVisible();
  await shot("inbox-empty");

  // 8. Settings, then the add-model dialog, then the six remaining sections.
  await page.goto("app://codeharness/");
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true");
  await page.locator(".settings").click();
  await expect(page.locator(".settings-nav")).toBeVisible();
  await shot("settings");
  await page.getByRole("button", { name: "افزودن مدل", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await shot("settings-add-model");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 30000 });
  const sections = ["settings-appearance", "settings-permissions", "settings-context", "settings-terminal", "settings-data", "settings-about"];
  for (const [index, name] of sections.entries()) {
    await page.locator(".settings-nav button").nth(index + 1).click();
    await shot(name);
  }

  // 9. The fixture provider, used for the one state a person cannot reproduce on demand:
  //    a model that asks for a path outside the workspace. The key goes into the vault
  //    first — the catalog refuses a model whose credential is missing — and a probe marks
  //    it usable.
  await api(page, "/internal/credentials", "POST", { id: "local", key: "synthetic-screens-key" });
  await api(page, "/models", "POST", { id: "local", name: "Local model", base_url: base, model: "local" });
  await api(page, "/models/local/test", "POST");

  // 10. Inbox: one real pending approval, left pending on purpose. The demo model reads,
  //     submits a plan (adopted automatically for a single low-risk step), starts it and
  //     then asks before the edit — the record the screenshot shows.
  const demoRun = await api<{ run_id: string }>(page, "/runs", "POST", { task: "demo edit src/app.py: return s => return s.strip()", workspace, model: "demo", mode: "ask" });
  type Record_ = { status: string; request: { run_id: string; approval_id: string; tool: string; path?: string | null } };
  const pending = async () => (await api<Record_[]>(page, "/approvals")).find(record => record.status === "pending" && record.request.run_id === demoRun.run_id && record.request.tool === "edit_file");
  await expect.poll(async () => Boolean(await pending()), { timeout: 90000 }).toBe(true);
  await page.goto("app://codeharness/approvals/");
  const row = page.locator(".inbox-row:not(.decided)").filter({ hasText: "src/app.py" }).first();
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.getByTestId("diff-view")).toBeVisible();
  await shot("inbox");
  await api(page, `/runs/${demoRun.run_id}/stop`, "POST");

  // 11. Errors: the jail card, from a real refusal by the permission layer. The run is
  //     started through the engine and opened from the sidebar, so the screenshot does not
  //     depend on the composer's state after the approvals detour.
  await api(page, "/runs", "POST", { task: "jail: read the forbidden SSH path", workspace, model: "local", mode: "ask" });
  await page.goto("app://codeharness/");
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true");
  const task = page.locator(".task-link").filter({ hasText: "jail" }).first();
  await expect(task).toBeVisible();
  await task.click();
  await expect(page.getByTestId("jail-card")).toBeVisible({ timeout: 90000 });
  await expect(page.locator(".stop")).toBeDisabled({ timeout: 90000 });
  await shot("errors");

  assert.equal(captured.length, 18, `expected 18 screens, captured ${captured.join(",")}`);
} finally {
  await app.close();
  // The fixture server can still hold a keep-alive socket from the engine; closing the
  // listener without dropping it leaves the process waiting.
  server.closeAllConnections();
  server.close();
}

console.log(`[screens] ${captured.length} images in docs/screenshots`);
