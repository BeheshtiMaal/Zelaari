/**
 * Phase 3 desktop pass: open a workspace, read a file, approve and reject a real
 * tool call through the temporary modal, and watch the file change or not change.
 *
 * Run after `npm run build`: `npx tsx tests/phase3-desktop.ts`.
 */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, mkdir, readFile, writeFile, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { _electron as electron, expect, type ElectronApplication, type Page } from "@playwright/test";

const artifacts = resolve("artifacts/phase3");
await mkdir(artifacts, { recursive: true });
const profile = await mkdtemp(join(tmpdir(), "harness-phase3-profile-"));
const workspace = await mkdtemp(join(tmpdir(), "harness-phase3-project-"));
await mkdir(join(workspace, "src"));
await mkdir(join(workspace, ".harness", "runs"), { recursive: true });
await writeFile(join(workspace, "README.md"), "# Phase three\n");
await writeFile(join(workspace, "src", "main.py"), "print('hello')\n");

/** A silent harness makes a hang indistinguishable from slowness; name every step. */
function step(name: string): void {
  console.log(`[${new Date().toISOString().slice(11, 19)}] ${name}`);
}

/** One tool call per conversation, then a closing turn. */
const server = createServer(async (request, response) => {
  if (request.url === "/v1/models") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ data: [{ id: "fixture", context_window: 65536 }] }));
    return;
  }
  let body = "";
  for await (const part of request) body += String(part);
  const input = JSON.parse(body) as {
    model: string; stream?: boolean; tools: { function: { name: string } }[];
    messages: { role: string; content: string }[];
  };
  const probe = input.tools?.some(tool => tool.function.name === "harness_probe");
  const answered = input.messages.some(message => message.role === "tool");
  const task = input.messages.find(message => message.role === "user")?.content ?? "";
  const target = task.includes("reject") ? "rejected.txt" : "approved.txt";
  const call = probe ? { name: "harness_probe", arguments: '{"marker":"connection-ok"}' } :
    answered ? undefined : { name: "write_file", arguments: JSON.stringify({ file_path: target, content: "written by the agent\n" }) };
  const content = call ? "" : 'root = Callout("done");';
  const tools = call ? [{ id: `call-${Date.now()}`, type: "function", function: call }] : undefined;
  response.writeHead(200, { "Content-Type": input.stream ? "text/event-stream" : "application/json" });
  if (input.stream) {
    const chunk = (delta: unknown, finish: string | null = null) => ({
      id: "fixture", object: "chat.completion.chunk", model: input.model,
      choices: [{ index: 0, delta, finish_reason: finish }],
    });
    for (const packet of [
      chunk({ role: "assistant" }),
      chunk({ content, ...(tools ? { tool_calls: tools.map((tool, index) => ({ ...tool, index })) } : {}) }),
      chunk({}, call ? "tool_calls" : "stop"),
      { id: "fixture", model: input.model, choices: [], usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 } },
    ]) response.write(`data: ${JSON.stringify(packet)}\n\n`);
    response.end("data: [DONE]\n\n");
  } else {
    response.end(JSON.stringify({
      id: "fixture", type: "chat.completion", model: input.model,
      choices: [{ index: 0, message: { role: "assistant", content, tool_calls: tools }, finish_reason: call ? "tool_calls" : "stop" }],
      usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
    }));
  }
});
await new Promise<void>(accept => server.listen(0, "127.0.0.1", accept));
const address = server.address();
assert.ok(address && typeof address === "object");
const base = `http://127.0.0.1:${address.port}/v1`;

async function launch(): Promise<ElectronApplication> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  }
  return electron.launch({ args: [process.cwd()], env: { ...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
}

async function ready(page: Page): Promise<void> {
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
}

async function exists(path: string): Promise<boolean> {
  try { await stat(path); return true; } catch { return false; }
}

let app: ElectronApplication | undefined;
try {
  step("launching");
  app = await launch();
  step("launched");
  let page = await app.firstWindow({ timeout: 120000 });
  step("first window");
  page.setDefaultTimeout(20000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.name));
  await ready(page);

  step("adding the fixture model");
  // -- add the fixture model through the real settings flow -----------------
  await app.evaluate(({ dialog }, path) => {
    dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [path] });
  }, workspace);
  await page.getByTestId("pick-workspace").click();
  await expect(page.locator(".workspace-picker select")).not.toHaveValue("");
  await page.locator(".settings").click();
  await page.getByRole("button", { name: "افزودن مدل", exact: true }).click();
  await page.getByRole("textbox", { name: "نام نمایشی", exact: true }).fill("Fixture");
  await page.getByRole("textbox", { name: "نشانی پایه (Base URL)" }).fill(base);
  await page.locator('input[type="password"]').fill("synthetic-phase3-key");
  await page.getByRole("textbox", { name: "نام مدل", exact: true }).fill("fixture");
  await page.getByRole("button", { name: "آزمایش اتصال", exact: true }).click();
  await expect(page.locator(".model-dialog .success")).toBeVisible({ timeout: 120000 });
  await page.getByRole("button", { name: "ذخیره", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 30000 });
  await page.locator(".model-card").filter({ hasText: "Fixture" }).getByRole("button", { name: "انتخاب پیش‌فرض", exact: true }).click();
  await page.locator(".sidebar nav button").first().click();
  await expect(page.locator(".composer-frame")).toBeVisible();

  step("workspace page");
  // -- the workspace page ---------------------------------------------------
  await page.goto(`app://codeharness/workspaces/?path=${encodeURIComponent(workspace)}`);
  await ready(page);
  await expect(page.locator(".ws-name")).toHaveText(workspace.split(/[\\/]/).pop() ?? "");
  await expect(page.locator(".ws-row").filter({ hasText: "src" })).toBeVisible();
  await expect(page.locator(".ws-row").filter({ hasText: ".harness" })).toHaveCount(0);
  await page.locator(".ws-system input").check();
  await expect(page.locator(".ws-row").filter({ hasText: ".harness" })).toBeVisible();
  await page.locator(".ws-row").filter({ hasText: "src" }).click();
  await page.locator(".ws-row").filter({ hasText: "main.py" }).click();
  await expect(page.locator(".ws-code")).toContainText("print('hello')");
  await page.screenshot({ path: join(artifacts, "workspace-fa.png") });

  step("approve flow");
  // -- approve: the modal appears before the tool runs ----------------------
  await page.goto("app://codeharness/");
  await ready(page);
  await page.locator("#task").fill("write the approved file");
  await page.locator("button[type=submit]").click();
  await expect(page.getByTestId("approval-modal")).toBeVisible({ timeout: 60000 });
  await expect(page.getByTestId("approval-target")).toHaveText("approved.txt");
  assert.equal(await exists(join(workspace, "approved.txt")), false, "the tool ran before approval");
  await page.screenshot({ path: join(artifacts, "approval-modal-fa.png") });
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("approval-modal")).toHaveCount(0, { timeout: 30000 });
  await expect(page.locator(".stop")).toBeDisabled({ timeout: 60000 });
  assert.equal(await readFile(join(workspace, "approved.txt"), "utf8"), "written by the agent\n");

  step("reject flow");
  // -- reject: Esc keeps the file absent and the run still finishes ---------
  await page.locator(".sidebar nav button").first().click();
  await page.locator("#task").fill("write the rejected file");
  await page.locator("button[type=submit]").click();
  await expect(page.getByTestId("approval-modal")).toBeVisible({ timeout: 60000 });
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("approval-modal")).toHaveCount(0, { timeout: 30000 });
  await expect(page.locator(".stop")).toBeDisabled({ timeout: 60000 });
  assert.equal(await exists(join(workspace, "rejected.txt")), false, "a rejected write still happened");

  assert.deepEqual(errors, []);
  console.log("Phase 3: desktop pass complete");
} finally {
  await app?.close();
  server.close();
}
