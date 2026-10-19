import assert from "node:assert/strict";
import { createServer } from "node:http";
import { randomBytes } from "node:crypto";
import { mkdtemp, mkdir, readFile, writeFile, readdir } from "node:fs/promises";
import { tmpdir, homedir } from "node:os";
import { resolve, join } from "node:path";
import { _electron as electron, expect, type ElectronApplication } from "@playwright/test";
import type { ModelInput } from "../src/lib/protocol";

const artifacts = resolve("artifacts/phase2");
await mkdir(artifacts, {recursive: true});
const profile = await mkdtemp(join(tmpdir(), "harness-phase2-profile-"));
const workspace = await mkdtemp(join(tmpdir(), "harness-phase2-project-"));
await mkdir(join(workspace, ".git"));
await writeFile(join(workspace, ".git/HEAD"), "ref: refs/heads/phase-two\n");
await writeFile(join(workspace, "README.md"), "marker=silver-maple\n");
const canary = "synthetic-" + randomBytes(24).toString("hex");
const replacement = "replacement-" + randomBytes(24).toString("hex");
const counts: Record<string, number> = {};
const server = createServer(async (request, response) => {
  if (request.url === "/v1/models") { response.writeHead(200, {"Content-Type": "application/json"}); response.end(JSON.stringify({data: [{id: "fixture", context_window: 65536}]})); return; }
  let body = "";
  for await (const part of request) body += String(part);
  const input = JSON.parse(body) as {model: string; stream?: boolean; tools: {function: {name: string}}[]; messages: {role: string; content: string}[]};
  counts[input.model] = (counts[input.model] ?? 0) + 1;
  const responseId = `response-${input.model}-${counts[input.model]}`;
  if (["unauthorized", "rate-limit"].includes(input.model)) {
    response.writeHead(input.model === "unauthorized" ? 401 : 429, {"Content-Type": "application/json"}); response.end(JSON.stringify({error: {message: canary}})); return;
  }
  const probe = input.tools?.some(tool => tool.function.name === "harness_probe");
  const done = input.messages.some(message => message.role === "tool");
  const call = input.model === "no-tools" ? undefined : probe ? {name: "harness_probe", arguments: '{"marker":"connection-ok"}'} : !done ? {name: "read_file", arguments: '{"file_path":"README.md"}'} : undefined;
  const content = call ? "" : `root = Stack([Callout("Done"), KeyValue("File", "silver-maple ${canary}")]);`;
  const tools = call ? [{id: "fixture-call", type: "function", function: call}] : undefined;
  response.writeHead(200, {"Content-Type": input.stream ? "text/event-stream" : "application/json"});
  if (input.stream) {
    const chunk = (delta: unknown, finish: string | null = null) => ({id: responseId, object: "chat.completion.chunk", model: input.model, choices: [{index: 0, delta, finish_reason: finish}]});
    const packets = [chunk({role: "assistant", reasoning_content: `Fixture reasoning ${canary}`}), chunk({content, ...(tools ? {tool_calls: tools.map((tool, index) => ({...tool, index}))} : {})}), chunk({}, call ? "tool_calls" : "stop"), {id: "fixture-response", model: input.model, choices: [], usage: {prompt_tokens: 100, completion_tokens: 20, total_tokens: 120}}];
    for (const packet of packets) response.write(`data: ${JSON.stringify(packet)}\n\n`);
    response.end("data: [DONE]\n\n");
  } else response.end(JSON.stringify({id: "fixture-response", type: "chat.completion", model: input.model, choices: [{index: 0, message: {role: "assistant", content, tool_calls: tools}, finish_reason: call ? "tool_calls" : "stop"}], usage: {prompt_tokens: 100, completion_tokens: 20, total_tokens: 120}}));
});
await new Promise<void>(accept => server.listen(0, "127.0.0.1", accept));
const address = server.address(); assert.ok(address && typeof address === "object");
const base = `http://127.0.0.1:${address.port}/v1`;
const evidence: Record<string, unknown> = {};
async function launch() {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  return electron.launch({args: [process.cwd()], env: {...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0"}, timeout: 120000});
}
let app: ElectronApplication | undefined;
try {
  app = await launch();
  console.log("Phase 2: desktop launched");
  let page = await app.firstWindow({timeout: 120000}); page.setDefaultTimeout(20000);
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.name));
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", {timeout: 60000});
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator(".empty-state")).toHaveCount(2);
  await page.screenshot({path: join(artifacts, "home-empty-fa.png")});
  await app.evaluate(({dialog}) => { dialog.showOpenDialog = async () => ({canceled: true, filePaths: []}); });
  await page.getByTestId("pick-workspace").click();
  await expect(page.locator(".workspace-picker select")).toHaveValue("");
  for (const forbidden of [resolve(workspace).slice(0, 3), homedir()]) {
    await app.evaluate(({dialog}, path) => { dialog.showOpenDialog = async () => ({canceled: false, filePaths: [path]}); }, forbidden);
    await page.getByTestId("pick-workspace").click();
    await expect(page.locator(".workspace-picker select")).toHaveValue("");
  }
  await app.evaluate(({dialog}, path) => { dialog.showOpenDialog = async () => ({canceled: false, filePaths: [path]}); }, workspace);
  await page.getByTestId("pick-workspace").click();
  await expect(page.getByTestId("branch")).toContainText("phase-two");
  await page.locator(".settings").click();
  await expect(page.locator(".settings-nav button")).toHaveCount(7);
  for (let index = 2; index < 7; index++) {
    await page.locator(".settings-nav button").nth(index).click();
    await expect(page.locator(".deferred-panel")).toBeVisible();
  }
  await page.locator(".settings-nav button").first().click();
  await page.getByRole("button", {name: "افزودن مدل", exact: true}).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("button", {name: "Jev", exact: true})).toBeDisabled();
  await expect(page.getByRole("button", {name: "Metis", exact: true})).toBeDisabled();
  await page.getByRole("button", {name: "AvalAI", exact: true}).click();
  await expect(page.getByRole("textbox", {name: "نشانی پایه (Base URL)"})).toHaveValue("https://api.avalai.ir/v1");
  await page.screenshot({path: join(artifacts, "dialog-fa.png")});
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", {name: "افزودن مدل", exact: true}).click();
  await page.getByRole("textbox", {name: "نام نمایشی", exact: true}).fill("Local provider");
  await page.getByRole("textbox", {name: "نشانی پایه (Base URL)"}).fill(base);
  await page.locator('input[type="password"]').fill(canary);
  await page.getByRole("textbox", {name: "نام مدل", exact: true}).fill("fixture");
  await page.getByRole("button", {name: "آزمایش اتصال", exact: true}).click();
  console.log("Phase 2: draft probe submitted");
  await expect(page.locator(".model-dialog .success")).toBeVisible({timeout: 120000});
  // Draft testing must not persist a provider or a plaintext key.
  assert.equal((JSON.parse(await readFile(join(profile, "catalog.json"), "utf8")) as {models: object}).models && Object.keys((JSON.parse(await readFile(join(profile, "catalog.json"), "utf8")) as {models: object}).models).length, 0);
  await page.getByRole("button", {name: "ذخیره", exact: true}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0, {timeout: 30000});
  const card = page.locator(".model-card").filter({hasText: "Local provider"});
  await expect(card.locator(".success")).toBeVisible();
  await expect(card).toContainText("۶۵٬۵۳۶");
  await card.getByRole("button", {name: "انتخاب پیش‌فرض", exact: true}).click();
  await card.getByRole("button", {name: "ویرایش", exact: true}).click();
  await expect(page.locator('input[type="password"]')).toHaveValue("");
  await page.getByRole("button", {name: "ذخیره", exact: true}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.screenshot({path: join(artifacts, "models-fa.png")});
  await page.locator(".settings-nav button").nth(1).click();
  await page.getByRole("button", {name: "English", exact: true}).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await page.screenshot({path: join(artifacts, "appearance-en.png")});
  await page.locator(".sidebar nav button").first().click();
  await page.locator(".hints button").first().click();
  await expect(page.locator("#task")).toHaveValue("Fix a bug");
  await page.locator("#task").fill("read README.md");
  await page.getByRole("combobox", {name: "With approval", exact: true}).selectOption("read-only");
  await page.screenshot({path: join(artifacts, "home-en.png")});
  await page.locator("button[type=submit]").click();
  await expect(page.getByTestId("keyvalue")).toContainText("silver-maple", {timeout: 45000});
  await expect(page.locator(".stop")).toBeDisabled();
  await expect(page.getByTestId("token-meter")).toHaveText("240 tokens");
  await expect(page.getByTestId("keyvalue")).toContainText("[REDACTED]");
  await page.screenshot({path: join(artifacts, "run-en.png")});
  const beforeReplay = counts.fixture;
  const catalog = JSON.parse(await readFile(join(profile, "catalog.json"), "utf8")) as {models: Record<string, {id: string}>; workspaces: {tasks: {id: string; mode: string}[]}};
  const id = Object.keys(catalog.models)[0];
  assert.equal(catalog.workspaces.tasks[0].mode, "read-only");
  const savedRun = catalog.workspaces.tasks[0].id;
  const events = await readFile(join(workspace, `.harness/runs/${savedRun}/events.jsonl`), "utf8");
  assert.ok(events.includes("reasoning.delta") && !events.includes(canary));
  await app.close(); app = undefined;
  app = await launch(); page = await app.firstWindow({timeout: 120000}); page.setDefaultTimeout(20000);
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", {timeout: 60000});
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.locator(".model-select select")).toHaveValue(id);
  await expect(page.getByTestId("branch")).toContainText("phase-two");
  await page.locator(".workspace-history summary").first().click();
  await expect(page.locator(".task-link")).not.toBeVisible();
  await page.locator(".workspace-history summary").first().click();
  await page.locator(".task-link").first().click();
  await expect(page.getByTestId("keyvalue")).toContainText("silver-maple");
  await expect(page.getByTestId("token-meter")).toHaveText("240 tokens");
  assert.equal(counts.fixture, beforeReplay, "Reopening history must not call the model");
  await page.locator(".settings").click();
  const savedCard = page.locator(".model-card").filter({hasText: "Local provider"});
  await expect(savedCard.locator(".success")).toBeVisible();
  await savedCard.getByRole("button", {name: "Edit", exact: true}).click();
  await page.locator('input[type="password"]').fill(replacement);
  await page.getByRole("button", {name: "Save", exact: true}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(savedCard).toContainText("Connection not tested yet");
  await savedCard.getByRole("button", {name: "Test", exact: true}).click();
  await expect(savedCard.locator(".success")).toBeVisible({timeout: 30000});
  const failures = ["unauthorized", "rate-limit", "no-tools"];
  for (const model of failures) {
    const value: ModelInput & {api_key: string} = {id: model, name: model, model, base_url: base, api_key: canary};
    assert.ok(await page.evaluate(async data => (await window.harness!.saveModel(data)).ok, value));
    const result = await page.evaluate(async modelId => {
      const h = window.harness!;
      const r = await fetch(`${h.baseUrl}/models/${modelId}/test`, {method: "POST", headers: {Authorization: `Bearer ${h.token}`}});
      return r.json() as Promise<{probe: {code: string}}>;
    }, model);
    assert.equal(result.probe.code, model === "unauthorized" ? "unauthorized" : model === "rate-limit" ? "rate_limit" : "no_tools");
    const denied = await page.evaluate(async ({model, workspace}) => {
      const h = window.harness!, headers = {Authorization: `Bearer ${h.token}`, "Content-Type": "application/json"};
      const setting = await fetch(h.baseUrl + "/settings", {method: "PUT", headers, body: JSON.stringify({locale: "en", default_model: model})});
      const run = await fetch(h.baseUrl + "/runs", {method: "POST", headers, body: JSON.stringify({task: "read README.md", workspace, model})});
      return [setting.status, run.status];
    }, {model, workspace});
    assert.deepEqual(denied, [400, 400]);
  }
  await page.reload(); await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true");
  await page.locator(".settings").click();
  await expect(page.locator(".provider-error")).toHaveCount(3);
  await expect(page.locator(".model-card .text-button:disabled")).toHaveCount(3);
  await page.screenshot({path: join(artifacts, "errors-en.png")});
  assert.equal(counts["rate-limit"], 3);
  await page.locator(".settings-nav button").nth(1).click();
  await page.getByRole("button", {name: "فارسی", exact: true}).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page.screenshot({path: join(artifacts, "appearance-fa.png")});
  await page.locator(".settings-nav button").first().click();
  await page.screenshot({path: join(artifacts, "errors-fa.png")});
  await app.evaluate(({safeStorage}) => { safeStorage.isEncryptionAvailable = () => false; });
  const blocked = await page.evaluate(async ({base, canary}) => window.harness!.saveModel({id: "blocked", name: "blocked", model: "fixture", base_url: base, api_key: canary}), {base, canary});
  assert.equal(blocked.ok, false);
  await page.reload(); await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true");
  await page.locator(".settings").click();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await app.evaluate(({BrowserWindow}) => BrowserWindow.getAllWindows()[0].setContentSize(800, 600));
  const addButton = page.getByRole("button", {name: "افزودن مدل", exact: true});
  await addButton.click();
  await expect(page.locator(".model-dialog input")).toHaveCount(4);
  await page.locator('[aria-label="Jev: URL pending"]').focus();
  await expect(page.getByRole("tooltip")).toHaveText("URL pending");
  for (let tab = 0; tab < 15; tab++) {
    await page.keyboard.press("Tab");
    assert.ok(await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]')));
  }
  await page.screenshot({path: join(artifacts, "dialog-small-fa.png")});
  // A focused tooltip consumes Escape before the enclosing dialog does.
  await page.keyboard.press("Escape");
  if (await page.getByRole("dialog").count()) await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(addButton).toBeFocused();
  await page.locator(".sidebar nav button").first().click();
  await page.locator(".worktree").locator("..").focus();
  await expect(page.getByRole("tooltip")).toContainText("۳");
  await page.locator(".context-ring").locator("..").focus();
  await expect(page.getByRole("tooltip")).toContainText("۷");
  assert.ok(await page.locator(".surface").evaluate(element => element.scrollWidth <= element.clientWidth));
  await page.screenshot({path: join(artifacts, "home-small-fa.png")});
  await page.locator(".settings").click();
  await page.locator(".settings-nav button").nth(1).click();
  await page.getByRole("button", {name: "English", exact: true}).click();
  await page.locator(".sidebar nav button").first().click();
  assert.ok(await page.locator(".surface").evaluate(element => element.scrollWidth <= element.clientWidth));
  await page.screenshot({path: join(artifacts, "home-small-en.png")});
  await app.close(); app = undefined;
  async function scan(path: string): Promise<number> {
    let files = 0;
    for (const entry of await readdir(path, {withFileTypes: true})) {
      const target = join(path, entry.name);
      if (entry.isDirectory()) files += await scan(target);
      else { const data = await readFile(target); assert.ok(!data.includes(Buffer.from(canary)) && !data.includes(Buffer.from(replacement)), "Canary found in persisted artifact"); files++; }
    }
    return files;
  }
  evidence.scannedFiles = await scan(profile) + await scan(workspace);
  evidence.requests = counts; evidence.rendererErrors = errors;
  assert.deepEqual(errors, []);
  evidence.passed = ["native picker refusal/cancel", "DPAPI save/retention/restart/fail-closed", "draft probe does not save", "context metadata", "language restart", "real compatible tool run", "reasoning/usage", "task replay", "401/429/no-tools UI", "canary artifacts", "modal focus/escape/return", "pending/ring/worktree tooltips", "800x600 RTL/LTR"];
  await writeFile(join(artifacts, "desktop.json"), JSON.stringify(evidence, null, 2));
  console.log("Phase 2 desktop checks passed; live endpoints were not contacted.");
} catch (error) {
  const safe = String(error).replaceAll(canary, "[REDACTED]").replaceAll(replacement, "[REDACTED]");
  console.error(safe);
  if (app) {
    const page = await app.firstWindow().catch(() => null);
    const text = page ? await page.locator("body").innerText().catch(() => "unavailable") : "unavailable";
    await writeFile(join(artifacts, "failure.txt"), safe + "\nrequests=" + JSON.stringify(counts) + "\n" + text.replaceAll(canary, "[REDACTED]").replaceAll(replacement, "[REDACTED]"));
  }
  throw new Error("Phase 2 desktop check failed; see sanitized artifacts/phase2/failure.txt");
} finally { await app?.close().catch(() => undefined); server.closeAllConnections(); server.close(); }
