/**
 * Phase 8 walkthrough: the Customize hub, skills as folders, the search gate and MCP.
 *
 * Real Electron, real engine, real loader and scan, real connector processes, offline
 * scripted models. Every assertion reads DOM state, a persisted event, a file on disk or
 * what a local server actually received. Screenshots are evidence, never the assertion.
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { _electron as electron, expect as baseExpect, type Page } from "@playwright/test";
import type { ApprovalRecord, HarnessEvent, SkillRecord } from "../src/lib/protocol";

const expect = baseExpect.configure({ timeout: 60000 });
const root = process.cwd(), python = resolve(root, "backend/.venv/Scripts/python.exe");
const artifacts = resolve(root, "artifacts/phase8");
await mkdir(artifacts, { recursive: true });

/** Only the scenarios named here run; the whole suite runs when it is unset. */
const only = process.env.PHASE8_ONLY?.split(",").map(name => name.trim()).filter(Boolean) ?? null;
const wanted = (id: string) => only === null || only.includes(id);

const workspace = await mkdtemp(join(tmpdir(), "harness-phase8-project-"));
const profile = await mkdtemp(join(tmpdir(), "harness-phase8-profile-"));
const incoming = await mkdtemp(join(tmpdir(), "harness-phase8-incoming-"));
const evidence: string[] = [], errors: string[] = [], facts: Record<string, unknown> = {};

const env: Record<string, string> = {};
for (const [key, value] of Object.entries(process.env)) {
  if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
}
env.PATH = `${resolve(root, "backend/.venv/Scripts")};${env.PATH ?? ""}`;

const seeded = JSON.parse(execFileSync(python, [resolve("backend/tests/phase8_seed.py"), workspace], {
  env: { ...env, NODE_ENV: "production", PYTHONPATH: resolve("backend"), LANGSMITH_TRACING: "false", LANGCHAIN_TRACING_V2: "false" },
  windowsHide: true, timeout: 120000, encoding: "utf8",
}).trim().split(/\r?\n/).at(-1)!) as {
  workspace: string; skill: string; description: string; marker: string; server: string; python: string; skills: number;
};

/** Two folders to install from: one approved, one refused. */
const SKILL_SOURCE = `---
name: changelog-writer
description: Turn a list of merged changes into one short changelog entry per release.
command: /changelog
category: docs
---

# Changelog writer

Write the entry for the person reading a release page, not for the reviewer of the change.

## Shape

- One line per release, newest first.
- The verb first: added, changed, fixed, removed.
- A link only when the reader can act on it.
`;
const REJECT_SOURCE = `---
name: refused-skill
description: A skill the person decides not to install.
---

# Refused skill

This folder must not appear in the workspace after a rejected approval.
`;
await mkdir(join(incoming, "changelog-writer"), { recursive: true });
await writeFile(join(incoming, "changelog-writer", "SKILL.md"), SKILL_SOURCE);
await mkdir(join(incoming, "refused-skill"), { recursive: true });
await writeFile(join(incoming, "refused-skill", "SKILL.md"), REJECT_SOURCE);

/** A SearXNG-shaped endpoint that records every query it is given. */
const queries: string[] = [];
const search = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  queries.push(url.searchParams.get("q") ?? "");
  response.writeHead(200, { "content-type": "application/json" });
  response.end(JSON.stringify({
    results: [
      { title: "Release notes that people read", url: "https://example.invalid/release-notes", content: "One section per change." },
      { title: "Changelog conventions", url: "https://example.invalid/changelog", content: "Keep the verb first." },
    ],
  }));
});
await new Promise<void>(done => search.listen(0, "127.0.0.1", done));
const searchUrl = `http://127.0.0.1:${(search.address() as AddressInfo).port}`;

const app = await electron.launch({ args: [root], env: { ...env, CODEHARNESS_TEST_USER_DATA: profile, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
const page = await app.firstWindow();
page.setDefaultTimeout(60000);
page.on("pageerror", error => errors.push(error.message));

async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  return page.evaluate(async ({ path, method, body }) => {
    const bridge = window.harness!;
    const response = await fetch(bridge.baseUrl + path, { method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }, { path, method, body });
}
async function shot(name: string) { await page.screenshot({ path: join(artifacts, `${name}.png`), scale: "css" }); }
const query = `?workspace=${encodeURIComponent(workspace)}`;

/** Decide a configuration approval without leaving the screen that proposed it. */
async function decide(record: ApprovalRecord, decision: "approve" | "reject") {
  return api(`/runs/${encodeURIComponent(record.request.run_id)}/interrupts/${encodeURIComponent(record.request.approval_id)}`, "POST", { decision, reason: null, revision: null });
}
/** The inbox path: the person opens the card, reads it and decides. */
async function decideInInbox(name: string, decision: "approve" | "reject" = "approve") {
  await page.locator('a[href="/approvals/"]').click();
  await expect(page.locator(".inbox-row").first()).toBeVisible({ timeout: 30000 });
  await page.locator(".inbox-row").filter({ hasText: name }).first().click();
  await expect(page.getByTestId("approval-card")).toBeVisible();
  await page.getByTestId(decision === "approve" ? "approval-approve" : "approval-reject").click();
  await expect(page.locator(".inbox-row").filter({ hasText: name }).first().locator(".risk-badge")).not.toHaveText("منتظر", { timeout: 30000 });
}
async function openCustomize(tab = "skills") {
  await page.locator('a[href="/customize/"]').click();
  await expect(page.locator(".customize-screen")).toBeVisible();
  await page.getByTestId(`customize-tab-${tab}`).click();
}
async function start(task: string): Promise<string> {
  await page.locator(".sidebar nav button").first().click();
  await page.locator(".workspace-toolbar select").last().selectOption("auto");
  await page.locator("#task").fill(task);
  const created = page.waitForResponse(response => new URL(response.url()).pathname === "/runs" && response.request().method() === "POST");
  await page.locator("#task").press("Enter");
  return (await (await created).json() as { run_id: string }).run_id;
}
async function status(text: string) {
  await expect(page.locator(".run-header [role=status]")).toHaveText(text, { timeout: 180000 });
}
async function log(runId: string): Promise<HarnessEvent[]> {
  const text = await readFile(join(workspace, ".harness", "runs", runId, "events.jsonl"), "utf8");
  return text.trim().split(/\r?\n/).map(line => JSON.parse(line) as HarnessEvent);
}
async function prompt(runId: string): Promise<string> {
  return readFile(join(workspace, ".harness", "runs", runId, "system.md"), "utf8");
}
async function skills(): Promise<{ skills: SkillRecord[]; commands: { command: string; name: string }[] }> {
  return api(`/skills${query}`);
}
async function runTask(task: string): Promise<{ runId: string; prompt: string; events: HarnessEvent[] }> {
  const runId = await start(task);
  await status("پایان یافت");
  return { runId, prompt: await prompt(runId), events: await log(runId) };
}

try {
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 90000 });
  await api("/workspaces", "POST", { path: workspace });
  await api("/settings", "PUT", { locale: "fa", default_model: "demo" });
  await page.reload();
  await expect(page.locator("#task")).toBeEnabled({ timeout: 60000 });
  facts.fixtures = { workspace, profile, incoming, seeded, searchUrl };

  if (wanted("S1")) {
    // S1: the hub and the Skills tab are the mock: tabs, counts, filters, cards, detail.
    await openCustomize();
    for (const tab of ["skills", "agents", "rules", "memory", "connectors"]) {
      await expect(page.getByTestId(`customize-tab-${tab}`)).toBeVisible();
    }
    await expect(page.getByTestId("customize-tab-skills")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("customize-counts")).toBeVisible();
    await expect(page.getByTestId("skills-tab-installed")).toContainText("(۶)");
    await expect(page.getByTestId("skills-tab-market")).toContainText("بازار مهارت‌ها");
    await expect(page.getByTestId("skills-tab-mine")).toContainText("ساخته‌شده توسط من");
    await expect(page.getByTestId("skill-search")).toBeVisible();
    await expect(page.locator(".chips .chip")).toHaveCount(5);
    await expect(page.locator(".skill-card")).toHaveCount(6);
    await expect(page.locator(".skill-card [role=switch]")).toHaveCount(6);
    await expect(page.getByTestId("skill-add")).toBeVisible();
    // The approval-needing skill says so on its card; the project skill says where it lives.
    await expect(page.getByTestId("skill-card-web-search")).toContainText("نیازمند تأیید");
    await expect(page.getByTestId("skill-scan-release-notes")).toContainText("بررسی امنیتی ✓");
    await expect(page.getByTestId("skill-switch-web-search")).toHaveAttribute("aria-checked", "true");
    // The search box and the chips filter the same list the count describes.
    await page.getByTestId("skill-search").fill("web");
    await expect(page.locator(".skill-card")).toHaveCount(1);
    await page.getByTestId("skill-search").fill("");
    await page.locator(".chips .chip").filter({ hasText: "تست" }).click();
    await expect(page.locator(".skill-card")).toHaveCount(1);
    await page.locator(".chips .chip").filter({ hasText: "همه" }).click();
    await expect(page.locator(".skill-card")).toHaveCount(6);
    // `Made by me` is the project subset: one folder from this workspace.
    await page.getByTestId("skills-tab-mine").click();
    await expect(page.locator(".skill-card")).toHaveCount(1);
    await expect(page.getByTestId("skill-card-release-notes")).toContainText("پوشه‌ی پروژه");
    await page.getByTestId("skill-card-release-notes").locator(".skill-card-main").click();
    await expect(page.getByTestId("skill-detail")).toBeVisible();
    await expect(page.locator(".skill-facts > div")).toHaveCount(4);
    await expect(page.getByTestId("skill-source")).toContainText("name: release-notes");
    await expect(page.getByTestId("skill-source")).toContainText(seeded.marker);
    await shot("skills-tab-fa");
    await page.getByTestId("skills-tab-installed").click();
    await expect(page.locator(".skill-card")).toHaveCount(6);
    evidence.push(`S1 five tabs, six cards for ${seeded.skills} skills, five chips that filter, the needs-approval chip on web-search, a one-card project subset, and a detail panel with four rows and the SKILL.md body`);
  }

  if (wanted("S2")) {
    // S2: a folder install is a proposal; approving writes it, rejecting writes nothing.
    await openCustomize();
    await page.getByTestId("skill-add").click();
    await expect(page.getByTestId("install-dialog")).toBeVisible();
    await page.getByTestId("install-kind").selectOption("folder");
    await page.getByTestId("install-source").fill(join(incoming, "changelog-writer"));
    await page.getByTestId("install-submit").click();
    await expect(page.getByTestId("install-dialog")).toContainText("در صندوق تأیید منتظر تصمیم شماست.");
    assert.equal(existsSync(join(workspace, ".harness", "skills", "changelog-writer")), false, "a proposal wrote the folder");
    await shot("install-staged-fa");
    await page.getByTestId("install-dialog").getByRole("button", { name: "بستن" }).click();
    await decideInInbox("changelog-writer");
    await openCustomize();
    await expect(page.getByTestId("skill-card-changelog-writer")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("skill-scan-changelog-writer")).toContainText("بررسی امنیتی ✓");
    await expect(page.locator(".skill-card")).toHaveCount(7);
    await expect(page.getByTestId("skills-tab-installed")).toContainText("(۷)");
    assert.match(await readFile(join(workspace, ".harness", "skills", "changelog-writer", "SKILL.md"), "utf8"), /name: changelog-writer/);
    await shot("installed-fa");

    await page.getByTestId("skill-add").click();
    await page.getByTestId("install-source").fill(join(incoming, "refused-skill"));
    await page.getByTestId("install-submit").click();
    await expect(page.getByTestId("install-dialog")).toContainText("در صندوق تأیید منتظر تصمیم شماست.");
    await page.getByTestId("install-dialog").getByRole("button", { name: "بستن" }).click();
    await decideInInbox("refused-skill", "reject");
    await openCustomize();
    await expect(page.getByTestId("skill-card-refused-skill")).toHaveCount(0);
    assert.equal(existsSync(join(workspace, ".harness", "skills", "refused-skill")), false, "a rejected install wrote the folder");
    evidence.push("S2 a folder install was a proposal (no folder on disk), approving wrote .harness/skills/changelog-writer with a clean scan and a ۷ count, rejecting left refused-skill absent");
  }

  if (wanted("S3")) {
    // S3: the switch removes a skill from the commands and from the next run's prompt.
    await openCustomize();
    assert.ok((await skills()).commands.some(item => item.command === "/search"), "web-search starts enabled");
    await page.getByTestId("skill-switch-web-search").click();
    await expect(page.getByTestId("skill-switch-web-search")).toHaveAttribute("aria-checked", "false");
    await expect.poll(async () => (await skills()).commands.some(item => item.command === "/search")).toBe(false);
    await page.getByTestId("skill-switch-web-search").click();
    await expect.poll(async () => (await skills()).commands.some(item => item.command === "/search")).toBe(true);

    // A project skill off means its name is not in the prompt the next run sends.
    await page.getByTestId("skill-switch-release-notes").click();
    await expect(page.getByTestId("skill-switch-release-notes")).toHaveAttribute("aria-checked", "false");
    const off = await runTask("demo skill load release-notes");
    assert.ok(!off.prompt.includes("release-notes"), "a disabled skill stayed in the prompt");
    await expect.poll(async () => (await skills()).commands.some(item => item.command === "/notes")).toBe(false);
    await openCustomize();
    await page.getByTestId("skill-switch-release-notes").click();
    await expect(page.getByTestId("skill-switch-release-notes")).toHaveAttribute("aria-checked", "true");

    // Progressive disclosure: the body arrives as a tool result, never in the prompt.
    const load = await runTask("demo skill load release-notes");
    assert.ok(load.prompt.includes("release-notes"), "the enabled skill is named in the prompt");
    assert.ok(load.prompt.includes(seeded.description), "the description is the part that stays");
    assert.ok(!load.prompt.includes(seeded.marker), "the skill body reached the prompt");
    const loaded = load.events.filter(event => event.type === "skill.loaded");
    assert.equal(loaded.length, 1, "one skill.loaded for one load_skill call");
    assert.equal(loaded[0].type === "skill.loaded" ? loaded[0].name : null, "release-notes");
    const call = load.events.find(event => event.type === "tool.call" && event.name === "load_skill");
    assert.ok(call, "the model used the real load_skill tool");
    const result = load.events.find(event => event.type === "tool.result" && event.type === "tool.result" && event.call_id === (call.type === "tool.call" ? call.call_id : ""));
    assert.ok(result && result.type === "tool.result" && result.text.includes(seeded.marker), "the body came back as the tool result");
    evidence.push(`S3 the switch removed /search and /notes from the commands, a disabled skill left the prompt, and demo skill load called load_skill: the prompt names release-notes with its description but the body marker arrived only as the tool result`);
  }

  if (wanted("S4")) {
    // S4: web search asks in Auto, and the query the person edits is the one that runs.
    const record = await api<ApprovalRecord>(`/skills/search${query}`, "PUT", { provider: "searxng", endpoint: searchUrl });
    await decide(record, "approve");
    const runId = await start("demo web search release note format");
    const card = page.locator(".timeline").getByTestId("approval-card");
    await expect(card).toBeVisible({ timeout: 120000 });
    await expect(card.locator(".command-preview")).toContainText("release note format");
    await expect(card).toContainText("web_search");
    await shot("web-search-approval-fa");
    const edited = "release note checklist for maintainers";
    await card.getByRole("button", { name: "ویرایش ورودی", exact: true }).click();
    await card.locator(".approval-input textarea").first().fill(JSON.stringify({ query: edited, limit: 3 }));
    await card.getByRole("button", { name: "بررسی ورودی ویرایش‌شده", exact: true }).click();
    await expect(card.getByText("پیش از تأیید، ورودی و تغییرات تازه را بررسی کنید.", { exact: false })).toBeVisible();
    await card.getByTestId("approval-approve").click();
    await status("پایان یافت");
    assert.deepEqual(queries, [edited], "the provider received exactly the edited query");
    const events = await log(runId);
    const result = events.find(event => event.type === "tool.result" && event.type === "tool.result" && event.text.includes("example.invalid"));
    assert.ok(result, "the search result reached the conversation");
    evidence.push(`S4 in Auto the web_search call still asked; the card showed the model's query, the edit was reviewed, and the local provider received only "${edited}"`);
  }

  if (wanted("S5")) {
    // S5: adding a server is a proposal; once approved its tools join the gate.
    await openCustomize("connectors");
    await expect(page.getByTestId("server-detail")).toBeVisible();
    await page.getByTestId("server-add").click();
    await expect(page.getByTestId("server-dialog")).toBeVisible();
    await page.getByTestId("server-name").fill("fake");
    await page.getByTestId("server-command").fill(`"${seeded.python}" "${seeded.server}" normal`);
    await page.getByTestId("server-submit").click();
    await expect(page.getByTestId("server-dialog")).toContainText("در صندوق تأیید منتظر تصمیم شماست.");
    await shot("server-staged-fa");
    await page.getByTestId("server-dialog").getByRole("button", { name: "بستن" }).click();
    await decideInInbox("MCP server fake");
    await openCustomize("connectors");
    await expect(page.getByTestId("server-card-fake")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("server-card-fake")).toContainText("متصل");
    await page.getByTestId("server-card-fake").locator(".skill-card-main").click();
    await expect(page.getByTestId("server-tools")).toContainText("fake__echo");
    await expect(page.getByTestId("server-tools")).toContainText("fake__count");
    await shot("connectors-fa");

    const runId = await start("demo mcp call fake__echo");
    const card = page.locator(".timeline").getByTestId("approval-card");
    await expect(card).toBeVisible({ timeout: 120000 });
    await expect(card).toContainText("fake__echo");
    await shot("mcp-approval-fa");
    await card.getByTestId("approval-approve").click();
    await status("پایان یافت");
    const events = await log(runId);
    const result = events.find(event => event.type === "tool.result" && event.type === "tool.result" && event.text.includes("echo: ping"));
    assert.ok(result, "the MCP tool answered the call");
    evidence.push("S5 adding a stdio server asked for approval, the approved card showed متصل with fake__echo and fake__count, and a fake__echo call asked again before the server answered echo: ping");
  }

  if (wanted("S6")) {
    // S6: memory and a workspace agent both write through approval and reach the prompt.
    const memory = "This workspace ships release notes in Persian and English; keep both in step.";
    await openCustomize("memory");
    await page.getByTestId("memory-body").fill(memory);
    await page.getByTestId("memory-save").click();
    await expect(page.locator(".memory-form")).toContainText("در صندوق تأیید منتظر تصمیم شماست.");
    await decideInInbox("Workspace memory");
    await openCustomize("memory");
    await expect(page.getByTestId("memory-body")).toHaveValue(memory, { timeout: 30000 });
    await shot("memory-fa");

    await openCustomize("agents");
    await page.getByTestId("agent-add").click();
    await expect(page.getByTestId("agent-form")).toBeVisible();
    await page.getByTestId("agent-name").fill("docs-writer");
    await page.getByTestId("agent-description").fill("Reads the project and drafts documentation changes.");
    await page.getByTestId("agent-instructions").fill("Read README.md and the docs folder. Report what is stale. Never write.");
    await page.getByTestId("agent-submit").click();
    await expect(page.getByTestId("agent-form")).toContainText("در صندوق تأیید منتظر تصمیم شماست.");
    await decideInInbox("docs-writer");
    await openCustomize("agents");
    await expect(page.getByTestId("agent-card-docs-writer")).toBeVisible({ timeout: 30000 });
    await shot("agents-fa");

    const run = await runTask("demo skill load release-notes");
    assert.ok(run.prompt.includes(memory), "the saved memory is in the next run's prompt");
    assert.ok(run.prompt.includes("docs-writer"), "the workspace agent joined the delegates");
    assert.ok(!run.prompt.includes(seeded.marker), "the skill body is still out of the prompt");
    evidence.push("S6 memory saved through an approval appeared in the next run's prompt, and a workspace agent saved the same way joined the delegate list without widening its tools");
  }

  assert.deepEqual(errors, []);
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({ passed: true, evidence, facts, errors }, null, 2));
  console.log("Phase 8 walkthrough passed", evidence);
} catch (error) {
  console.error("[phase8] failure:", error);
  await shot("failure").catch(() => {});
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({ passed: false, evidence, facts, errors, failure: String(error) }, null, 2)).catch(() => {});
  throw error;
} finally {
  await app.close();
  search.close();
}
