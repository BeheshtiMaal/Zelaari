// Opt-in acceptance using external credentials. Never enable tracing or print errors.
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { _electron as electron, expect, type ElectronApplication } from "@playwright/test";
import type { Event, ProviderRecord, UsageUpdated } from "../src/lib/protocol";

const artifacts = resolve("artifacts/phase2-live");
const profile = await mkdtemp(join(tmpdir(), "harness-live-profile-"));
const workspace = await mkdtemp(join(tmpdir(), "harness-live-project-"));
let app: ElectronApplication | undefined;
const stage = { value: "load external credentials" };
try {
  const config = await readFile(join(process.env.APPDATA!, "CodeHarness/phase1-provider.env"), "utf8");
  const values = Object.fromEntries(config.replace(/^\uFEFF/, "").split(/\r?\n/).map(line => {
    const index = line.indexOf("=");
    return [line.slice(0, index).trim(), line.slice(index + 1).trim().replace(/^["']|["']$/g, "")];
  }));
  const key = values.CODEHARNESS_API_KEY;
  assert.ok(key);
  await mkdir(artifacts, {recursive: true});
  await writeFile(join(workspace, "README.md"), "# Live acceptance\nThe project tracks migrating swallows. Verification marker: amber-orbit.\n");
  const env: Record<string, string> = {};
  for (const [name, value] of Object.entries(process.env)) {
    if (value && name !== "ELECTRON_RUN_AS_NODE" && !name.endsWith("API_KEY") && !name.startsWith("LANGSMITH_") && !name.startsWith("LANGCHAIN_")) env[name] = value;
  }
  const launch = () => electron.launch({args: [process.cwd()], env: {...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0"}, timeout: 120000});
  app = await launch();
  let page = await app.firstWindow({timeout: 120000});
  page.setDefaultTimeout(30000);
  let rendererErrors = 0;
  page.on("pageerror", () => rendererErrors++);
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", {timeout: 60000});
  await page.locator(".settings").click();
  await page.locator(".settings-nav button").nth(1).click();
  await page.getByRole("button", {name: "English", exact: true}).click();
  await page.locator(".sidebar nav button").first().click();
  await app.evaluate(({dialog}, path) => { dialog.showOpenDialog = async () => ({canceled: false, filePaths: [path]}); }, workspace);
  await page.getByTestId("pick-workspace").click();
  const results: object[] = [];
  const cases = [
    {name: "Live OpenAI", model: "gpt-4o-mini", base: values.CODEHARNESS_BASE_URL, kind: "openai-compatible"},
    {name: "Live Claude", model: "claude-haiku-4-5", base: values.CODEHARNESS_BASE_URL, kind: "openai-compatible"},
  ];
  for (const provider of cases) {
    stage.value = `${provider.name}: add and probe`;
    await page.locator(".settings").click();
    await page.locator(".settings-nav button").first().click();
    await page.getByRole("button", {name: "Add model", exact: true}).click();
    await page.getByRole("textbox", {name: "Display name", exact: true}).fill(provider.name);
    await page.getByRole("textbox", {name: "Base URL", exact: true}).fill(provider.base);
    await page.locator('input[type="password"]').fill(key);
    await page.getByRole("textbox", {name: "Model name", exact: true}).fill(provider.model);
    await page.getByRole("button", {name: "Test connection", exact: true}).click();
    await expect(page.locator(".model-dialog .success")).toBeVisible({timeout: 120000});
    await page.getByRole("button", {name: "Save", exact: true}).click();
    await expect(page.getByRole("dialog")).toHaveCount(0, {timeout: 120000});
    const card = page.locator(".model-card").filter({hasText: provider.name});
    await expect(card.locator(".success")).toBeVisible();
    await card.getByRole("button", {name: "Make default", exact: true}).click();
    await page.screenshot({path: join(artifacts, `${provider.model}-settings.png`)});
    const metadata = JSON.parse(await readFile(join(profile, "catalog.json"), "utf8")) as {models: Record<string, ProviderRecord>};
    const record = Object.values(metadata.models).find(model => model.name === provider.name)!;
    assert.equal(record.kind, provider.kind);
    const id = record.id; assert.ok(id);
    stage.value = `${provider.name}: Home read`;
    await page.locator(".sidebar nav button").first().click();
    await expect(page.locator(".model-select select")).toHaveValue(id);
    await page.locator("#task").fill('Read README.md. Return a valid OpenUI program: root = Stack([Callout("Done"), KeyValue("Marker", "amber-orbit")]); use the actual file contents.');
    await page.locator("button[type=submit]").click();
    stage.value = `${provider.name}: running state`;
    await expect(page.locator(".stop")).toBeEnabled();
    stage.value = `${provider.name}: rendered output`;
    const outputSelector = '[data-testid="keyvalue"], [data-testid="fallback"], [data-testid="message-text"]';
    await expect(page.locator(outputSelector).filter({hasText: "amber-orbit"}).last()).toBeVisible({timeout: 120000});
    stage.value = `${provider.name}: completed state`;
    await expect(page.locator(".stop")).toBeDisabled({timeout: 30000});
    const catalog = JSON.parse(await readFile(join(profile, "catalog.json"), "utf8")) as {workspaces: {tasks: {id: string; model: string; status: string}[]}};
    const task = catalog.workspaces.tasks.find(task => task.model === record.id && task.status === "completed")!;
    assert.ok(task);
    const eventsPath = join(workspace, `.harness/runs/${task.id}/events.jsonl`);
    const text = await readFile(eventsPath, "utf8");
    const events = text.trim().split(/\r?\n/).map(line => JSON.parse(line) as Event);
    assert.ok(events.some(e => e.type === "tool.call" && e.name === "read_file"));
    assert.ok(events.some(e => e.type === "tool.result" && e.text.includes("amber-orbit")));
    assert.ok(events.filter(e => e.type === "message.delta").length > 1);
    const usage = events.filter((e): e is UsageUpdated => e.type === "usage.updated").at(-1)!;
    assert.equal(usage.estimated, false);
    const meter = `${new Intl.NumberFormat("en").format(usage.input_tokens + usage.output_tokens)} tokens`;
    await expect(page.getByTestId("token-meter")).toHaveText(meter);
    await page.screenshot({path: join(artifacts, `${provider.model}-run.png`)});
    stage.value = `${provider.name}: restart and replay`;
    await app.close(); app = undefined;
    app = await launch(); page = await app.firstWindow({timeout: 120000}); page.setDefaultTimeout(30000);
    page.on("pageerror", () => rendererErrors++);
    await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", {timeout: 60000});
    await expect(page.locator(".model-select select")).toHaveValue(id);
    const taskIndex = catalog.workspaces.tasks.findIndex(item => item.id === task.id);
    await page.locator(".task-link").nth(taskIndex).click();
    await expect(page.locator(outputSelector).filter({hasText: "amber-orbit"}).last()).toBeVisible();
    await expect(page.getByTestId("token-meter")).toHaveText(meter);
    assert.equal(await readFile(eventsPath, "utf8"), text);
    stage.value = `${provider.name}: Home Stop`;
    await page.locator(".sidebar nav button").first().click();
    await page.locator("#task").fill("Read README.md and give a detailed explanation.");
    await page.locator("button[type=submit]").click();
    await expect(page.locator(".stop")).toBeEnabled();
    const started = Date.now(); await page.locator(".stop").click();
    await expect(page.locator(".stop")).toBeDisabled();
    const stopMs = Date.now() - started;
    assert.ok(stopMs < 1000);
    results.push({model: provider.model, adapter: record.kind, context: record.context, inputTokens: usage.input_tokens, outputTokens: usage.output_tokens, reasoningReceived: events.some(e => e.type === "reasoning.delta"), stopMs, probe: true, homeRead: true, stream: true, restartReplay: true});
    console.log(`${provider.name}: probe, Home read, tokens, restart/replay and Stop passed`);
  }
  await app.close(); app = undefined;
  stage.value = "persisted credential scan";
  let scanned = 0;
  const scan = async (directory: string): Promise<void> => {
    for (const entry of await readdir(directory, {withFileTypes: true})) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) await scan(path);
      else if (entry.isFile()) { assert.ok(!(await readFile(path)).includes(Buffer.from(key))); scanned++; }
    }
  };
  await scan(profile); await scan(workspace);
  assert.equal(rendererErrors, 0);
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({results, scannedFiles: scanned, rendererErrors}, null, 2));
  console.log(`Live desktop acceptance passed; ${scanned} files scanned; no credential persisted.`);
} catch {
  const page = app?.windows()[0];
  if (page && await page.getByRole("dialog").count() === 0) await page.screenshot({path: join(artifacts, "failure.png")}).catch(() => {});
  console.error(`Live desktop check failed at ${stage.value}; diagnostics suppressed.`);
  process.exitCode = 1;
} finally {
  if (app) await app.close().catch(() => {});
}
