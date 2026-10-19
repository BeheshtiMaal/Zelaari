/**
 * Phase 3 desktop pass: open a workspace, read a file, approve and reject a real
 * tool call through the temporary modal, and watch the file change or not change.
 *
 * Run after `npm run build`: `npx tsx tests/phase3-desktop.ts`.
 */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { mkdtemp, mkdir, readFile, writeFile, stat, readdir } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { _electron as electron, expect, type ElectronApplication, type Page } from "@playwright/test";
import { fa } from "../src/i18n/fa";

const artifacts = resolve("artifacts/phase3");
await mkdir(artifacts, { recursive: true });
const profile = await mkdtemp(join(tmpdir(), "harness-phase3-profile-"));
const workspace = await mkdtemp(join(tmpdir(), "harness-phase3-project-"));
const original = "# Phase three\r\noriginal bytes\r\n";
await mkdir(join(workspace, "src"));
await mkdir(join(workspace, ".harness", "runs"), { recursive: true });
await writeFile(join(workspace, "README.md"), original);
await writeFile(join(workspace, "src", "main.py"), "print('hello')\n");

/** A silent harness makes a hang indistinguishable from slowness; name every step. */
function step(name: string): void {
  console.log(`[${new Date().toISOString().slice(11, 19)}] ${name}`);
}

const results: { task: string; content: string }[] = [];
const forbidden = "C:\\Users\\phase3-fixture\\.ssh\\id_rsa";
/** Real engine tools; the provider alone is deterministic and offline. */
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
  if (answered) results.push({ task, content: input.messages.filter(message => message.role === "tool").map(message => message.content).join("\n") });
  const target = task.includes("reject") ? "rejected.txt" : "approved.txt";
  let action = { name: "write_file", arguments: JSON.stringify({ file_path: target, content: "written by the agent\n" }) };
  if (task.includes("timeout")) action = { name: "run_command", arguments: JSON.stringify({ command: "Start-Sleep -Seconds 180", timeout: task.includes("300 seconds") ? 300 : task.includes("short") ? 1 : 120 }) };
  if (task.includes("jail")) action = { name: "read_file", arguments: JSON.stringify({ file_path: forbidden }) };
  if (task.includes("undo")) action = { name: "edit_file", arguments: JSON.stringify({ file_path: "README.md", old_string: "original bytes", new_string: "agent changed bytes" }) };
  if (task.includes("isolated")) action = { name: "write_file", arguments: JSON.stringify({ file_path: "isolated.txt", content: "worktree only\n" }) };
  const call = probe ? { name: "harness_probe", arguments: '{"marker":"connection-ok"}' } :
    answered ? undefined : action;
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
  await expect(page.getByTestId("worktree")).toBeDisabled();
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

  async function taskRun(task: string) {
    await page.locator(".sidebar nav button").first().click();
    await page.locator("#task").fill(task);
    await page.locator("button[type=submit]").click();
  }
  async function finish() {
    await expect(page.locator(".stop")).toBeDisabled({ timeout: 60000 });
    await expect(page.locator(".run-actions [role=status]")).toHaveText(fa.completed);
  }

  step("jail card and model continuation");
  await taskRun("jail: read the forbidden SSH path");
  await expect(page.getByTestId("jail-card")).toBeVisible({ timeout: 60000 });
  await expect(page.getByTestId("jail-card")).toHaveCSS("border-radius", "16px");
  await expect(page.getByTestId("jail-card")).toHaveCSS("border-inline-start-style", "solid");
  await expect(page.getByTestId("jail-card")).toContainText("حتی با تأیید");
  await expect(page.getByTestId("approval-modal")).toHaveCount(0);
  await finish();
  assert.ok(results.some(result => result.task.includes("jail") && result.content.includes("even with approval")));
  await page.screenshot({ path: join(artifacts, "jail-card-fa.png") });

  step("UI undo restores exact bytes");
  await taskRun("undo: edit README.md");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await page.keyboard.press("Enter");
  await finish();
  assert.notDeepEqual(await readFile(join(workspace, "README.md")), Buffer.from(original));
  await page.goto(`app://codeharness/workspaces/?path=${encodeURIComponent(workspace)}`);
  await ready(page);
  await page.locator(".ws-row").filter({ hasText: "README.md" }).click();
  await expect(page.locator(".ws-line.changed")).not.toHaveCount(0);
  await page.getByTestId("undo-file").click();
  await expect(page.locator(".ws-code")).toContainText("original bytes");
  assert.deepEqual(await readFile(join(workspace, "README.md")), Buffer.from(original));
  await page.screenshot({ path: join(artifacts, "undo-fa.png") });

  step("branch approval, rejection and dirty-tree failure");
  const git = (...args: string[]) => execFileSync("git", args, { cwd: workspace, encoding: "utf8", windowsHide: true });
  git("init", "-b", "main");
  git("config", "user.email", "fixture@example.test");
  git("config", "user.name", "Phase 3 fixture");
  git("add", "README.md"); git("commit", "-m", "initial");
  git("switch", "-c", "feature");
  await writeFile(join(workspace, "README.md"), "feature version\n");
  git("commit", "-am", "feature content"); git("switch", "main");
  await page.goto("app://codeharness/"); await ready(page);
  const branch = page.getByTestId("branch").locator("select");
  await expect(branch).toHaveValue("main");
  await branch.selectOption("feature");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  assert.equal(git("branch", "--show-current").trim(), "main");
  await page.keyboard.press("Escape");
  assert.equal(git("branch", "--show-current").trim(), "main");
  await branch.selectOption("feature");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await page.screenshot({ path: join(artifacts, "branch-approval-fa.png") });
  await page.keyboard.press("Enter");
  await expect(branch).toHaveValue("feature");
  assert.equal(git("branch", "--show-current").trim(), "feature");
  await branch.selectOption("main");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await page.keyboard.press("Enter"); await expect(branch).toHaveValue("main");
  const head = await readFile(join(workspace, ".git", "HEAD"));
  await writeFile(join(workspace, "README.md"), "local dirty content\n");
  await branch.selectOption("feature");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("branch-error")).toContainText("local changes");
  await expect(branch).toHaveValue("main");
  assert.deepEqual(await readFile(join(workspace, ".git", "HEAD")), head);
  await page.screenshot({ path: join(artifacts, "branch-dirty-fa.png") });
  await writeFile(join(workspace, "README.md"), original);

  step("isolated worktree run");
  await page.getByTestId("worktree").check();
  await taskRun("isolated worktree write");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await expect(page.getByTestId("approval-modal")).toContainText("worktree_create");
  assert.equal(await exists(join(workspace, "isolated.txt")), false);
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("approval-modal")).toContainText("write_file", { timeout: 60000 });
  await page.keyboard.press("Enter"); await finish();
  const worktrees = await readdir(join(workspace, ".harness", "worktrees"));
  assert.equal(worktrees.length, 1);
  assert.equal(await readFile(join(workspace, ".harness", "worktrees", worktrees[0], "isolated.txt"), "utf8"), "worktree only\n");
  assert.equal(await exists(join(workspace, "isolated.txt")), false);
  assert.deepEqual(await readFile(join(workspace, "README.md")), Buffer.from(original));
  await page.goto(`app://codeharness/workspaces/?path=${encodeURIComponent(workspace)}`); await ready(page);
  await expect(page.locator(".ws-task").filter({ hasText: "isolated worktree write" })).toBeVisible();
  await expect(page.locator(".ws-path")).toContainText("main");
  await page.screenshot({ path: join(artifacts, "worktree-fa.png") });

  step("real default 120-second timeout and dismiss");
  await page.goto("app://codeharness/"); await ready(page);
  await taskRun("timeout: run the sleeping command");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("timeout-card")).toBeVisible({ timeout: 160000 });
  await expect(page.getByTestId("timeout-card")).toHaveCSS("border-radius", "16px");
  await expect(page.getByTestId("timeout-card")).toContainText("۱۲۰");
  await finish();
  await page.screenshot({ path: join(artifacts, "timeout-card-fa.png") });
  await page.getByTestId("timeout-reject").click();
  await expect(page.getByTestId("timeout-card")).toHaveCount(0);
  await finish();

  step("timeout retry raises a fresh 300-second approval");
  await taskRun("short timeout: run the sleeping command");
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("timeout-card")).toBeVisible({ timeout: 30000 }); await finish();
  await page.getByTestId("timeout-retry").click();
  await expect(page.getByTestId("approval-modal")).toBeVisible();
  await expect(page.getByTestId("approval-modal")).toContainText("300");
  await page.screenshot({ path: join(artifacts, "timeout-retry-fa.png") });
  await page.keyboard.press("Escape"); await finish();

  assert.deepEqual(errors, []);
  console.log("Phase 3: desktop pass complete");
} finally {
  await app?.close();
  server.close();
}
