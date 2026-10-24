/**
 * Phase 7 walkthrough: real Electron, real engine, real commands, scripted offline models.
 *
 * Every assertion below reads DOM state, a persisted event, a file on disk or the process
 * tree. Nothing here needs a person to look at a window.
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { _electron as electron, expect as baseExpect, type Page } from "@playwright/test";
import { arcDash, compactTokens, percentLabel, ringLabel, usedPercent } from "../src/lib/context-format";
import type { HarnessEvent } from "../src/lib/protocol";

const expect = baseExpect.configure({ timeout: 60000 });
const root = process.cwd(), python = resolve(root, "backend/.venv/Scripts/python.exe");
const artifacts = resolve(root, "artifacts/phase7");
await mkdir(artifacts, { recursive: true });

/** Only the scenarios named here run; the whole suite runs when it is unset. */
const only = process.env.PHASE7_ONLY?.split(",").map(name => name.trim()).filter(Boolean) ?? null;
const wanted = (id: string) => only === null || only.includes(id);

const green = await mkdtemp(join(tmpdir(), "harness-phase7-green-"));
const red = await mkdtemp(join(tmpdir(), "harness-phase7-red-"));
const profile = await mkdtemp(join(tmpdir(), "harness-phase7-profile-"));
const evidence: string[] = [], errors: string[] = [], facts: Record<string, unknown> = {};

const env: Record<string, string> = {};
for (const [key, value] of Object.entries(process.env)) {
  if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
}
// `run_command` runs `pytest -q` through the shell: the engine's PATH must find the tool.
env.PATH = `${resolve(root, "backend/.venv/Scripts")};${env.PATH ?? ""}`;

const seeded = JSON.parse(execFileSync(python, [resolve("backend/tests/phase7_seed.py"), profile, green, red], {
  env: { ...env, NODE_ENV: "production", PYTHONPATH: resolve("backend"), LANGSMITH_TRACING: "false", LANGCHAIN_TRACING_V2: "false" },
  windowsHide: true, timeout: 180000, encoding: "utf8",
}).trim().split(/\r?\n/).at(-1)!) as { run_id: string; summary: string; bytes: number };

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
async function start(task: string): Promise<string> {
  await page.locator(".sidebar nav button").first().click();
  // The walkthrough runs in Auto: plans are adopted so the gate and the budgets are what
  // the scripted model meets, not an approval prompt.
  await page.locator(".workspace-toolbar select").last().selectOption("auto");
  await page.locator("#task").fill(task);
  const created = page.waitForResponse(response => new URL(response.url()).pathname === "/runs" && response.request().method() === "POST");
  await page.locator("#task").press("Enter");
  return (await (await created).json() as { run_id: string }).run_id;
}
async function status(text: string) {
  await expect(page.locator(".run-header [role=status]")).toHaveText(text, { timeout: 150000 });
}
async function log(workspace: string, runId: string): Promise<HarnessEvent[]> {
  const text = await readFile(join(workspace, ".harness", "runs", runId, "events.jsonl"), "utf8");
  return text.trim().split(/\r?\n/).map(line => JSON.parse(line) as HarnessEvent);
}
async function configure(patch: Record<string, Record<string, unknown>>, workspace = green) {
  const path = join(workspace, ".harness", "config.json");
  const current = JSON.parse(await readFile(path, "utf8")) as Record<string, Record<string, unknown>>;
  for (const [section, values] of Object.entries(patch)) current[section] = { ...current[section], ...values };
  await writeFile(path, JSON.stringify(current, null, 2));
}
function childrenOf(pid: number, names: string[]): number[] {
  const script = "import psutil,json,sys; p=psutil.Process(int(sys.argv[1])); print(json.dumps([c.pid for c in p.children(recursive=True) if c.name().lower() in json.loads(sys.argv[2])]))";
  return JSON.parse(execFileSync(python, ["-c", script, String(pid), JSON.stringify(names)], { encoding: "utf8", windowsHide: true })) as number[];
}
/** Open every step row so the assertions see what a person would after one click. */
async function expandAll() {
  for (const button of await page.locator(".step-card > button").all()) {
    if (await button.getAttribute("aria-expanded") === "false") await button.click();
  }
}
async function openSettings(section: number) {
  await page.locator(".settings").click();
  await page.locator(".settings-nav button").nth(section).click();
  await expect(page.locator(".settings-content h2")).toBeVisible();
}
async function chooseInCard(label: string) {
  const card = page.locator(".compose-region .question-exhausted");
  await card.locator("label.question-option").filter({ hasText: label }).locator("input[type=radio]").check();
}

try {
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 90000 });
  await api("/workspaces", "POST", { path: green });
  await api("/settings", "PUT", { locale: "fa", default_model: "demo" });
  await page.reload();
  await expect(page.locator("#task")).toBeEnabled({ timeout: 60000 });
  facts.fixtures = { green, red, seeded };
  // The seeded run compacted at 30 %; the settings screens are compared against the mock's
  // defaults, so the walkthrough puts the stored values back to 60 % and 8 messages.
  await configure({ context: { compaction_percent: 60, keep_messages: 8 } });

  if (wanted("S1")) {
    // S1: the gate blocks a finish the tool results do not support.
    const runId = await start("demo verify gate");
    await expect(page.getByTestId("verify-notice").first()).toContainText("pytest -q");
    await status("پایان یافت");
    const events = await log(green, runId);
    const required = events.filter(event => event.type === "verify.required");
    assert.equal(required.length, 1, "one gate decision for one unverified finish");
    assert.equal(required[0].type === "verify.required" ? required[0].command : null, "pytest -q");
    assert.equal(required[0].type === "verify.required" ? required[0].reason : null, "unverified_changes");
    const check = events.find(event => event.type === "tool.call" && event.name === "run_command" && event.args.command === "pytest -q");
    assert.ok(check, "the model ran the command the gate named");
    assert.ok(check.seq > required[0].seq, "the check ran after the gate blocked the finish");
    const callId = check.type === "tool.call" ? check.call_id : "";
    const result = events.find(event => event.type === "tool.result" && event.call_id === callId);
    assert.ok(result && result.type === "tool.result" && /"exit_code":\s*0/.test(result.text), "the check passed");
    assert.ok(events.some(event => event.type === "run.finished" && event.status === "completed"));
    assert.ok(!events.some(event => event.type === "message.delta" && event.text.includes("done without checks") && event.seq > required[0].seq), "the unverified answer never became the final one");
    await shot("gate-blocked-fa");
    evidence.push(`S1 gate blocked once for ${required[0].type === "verify.required" ? required[0].command : ""} (seq ${required[0].seq}), check at seq ${check.seq} returned 0`);
  }

  if (wanted("S2")) {
    // S2: three failed fix attempts raise the real exhausted card, then each choice behaves.
    await api("/workspaces", "POST", { path: red });
    await page.reload();
    await expect(page.locator("#task")).toBeEnabled();
    const first = await start("demo verify budget");
    await expect(page.locator(".compose-region .question-exhausted")).toBeVisible({ timeout: 120000 });
    await expect(page.locator(".compose-region .question-exhausted")).toContainText("۳ تلاش ناموفق");
    await expect(page.getByTestId("limit-fixes")).toContainText("۳ از ۳");
    await shot("exhausted-fa");
    const hint = "از جداکننده‌ی خط تیره استفاده کن";
    await chooseInCard("با یک راهنمایی دوباره تلاش کن");
    await page.locator(".question-hint textarea").fill(hint);
    await page.locator(".question-send").click();
    await status("پایان یافت");
    const retried = await log(red, first);
    assert.ok(retried.some(event => event.type === "question.answered"), "the card was answered on the real barrier");
    assert.match(await readFile(join(red, "parser.py"), "utf8"), new RegExp(`# guidance: ${hint}`));
    const fixed = await readFile(join(red, "parser.py"), "utf8");
    assert.ok(fixed.includes('text.split("-")'), "the retry applied the guidance to the fix");
    evidence.push(`S2 retry cleared the counter, carried "${hint}" into the model and left a fixed parser.py`);

    const changeRun = await start("demo verify budget");
    await expect(page.locator(".compose-region .question-exhausted")).toBeVisible({ timeout: 120000 });
    await chooseInCard("رویکرد را عوض کن");
    await page.locator(".question-send").click();
    // A different approach is a new plan; dropping the old step is reviewed even in Auto.
    await expect(page.getByTestId("approval-card")).toBeVisible({ timeout: 90000 });
    await page.getByTestId("approval-approve").click();
    await status("پایان یافت");
    const changed = await log(red, changeRun);
    const plans = changed.flatMap(event => event.type === "plan.created" ? [event.plan.revision] : []);
    assert.ok(plans.length >= 2, "change asked for a revised plan");
    assert.notEqual(plans.at(-1), plans[0], "the revision is a new one");
    evidence.push("S2 change required a plan revision before the next attempt");

    const stopRun = await start("demo verify budget");
    await expect(page.locator(".compose-region .question-exhausted")).toBeVisible({ timeout: 120000 });
    await chooseInCard("متوقف شو و گزارش بده");
    await page.locator(".question-send").click();
    await status("پایان یافت");
    const stopped = await log(red, stopRun);
    assert.ok(stopped.some(event => event.type === "run.finished" && event.status === "completed"));
    assert.match(await readFile(join(red, "parser.py"), "utf8"), /ValueError|split/);
    await shot("stopped-fa");
    evidence.push("S2 stop finished completed and left the broken parser on disk");

    const declinedRun = await start("demo verify budget");
    await expect(page.locator(".compose-region .question-exhausted")).toBeVisible({ timeout: 120000 });
    await page.locator(".question-decline").click();
    await status("پایان یافت");
    const declined = await log(red, declinedRun);
    assert.ok(declined.some(event => event.type === "question.answered" && event.answer.status === "declined"), "the card was declined on the real barrier");
    // Declining is the stop path: the gate is suspended, so it never blocks and never reports.
    assert.equal(declined.filter(event => event.type === "verify.required").length, 0, "the suspended gate stayed silent");
    assert.ok(declined.some(event => event.type === "run.finished" && event.status === "completed"));
    assert.match(await readFile(join(red, "parser.py"), "utf8"), /ValueError|split/);
    evidence.push("S2 declined behaved as stop: finished completed with the changes left on disk");
    await api("/workspaces", "POST", { path: green });
    await page.reload();
    await expect(page.locator("#task")).toBeEnabled();
  }

  if (wanted("S3")) {
    // S3: the caps stop the run cleanly, with no orphan command process.
    await configure({ verify: { max_steps: 4 } });
    const stepsRun = await start("demo verify budget");
    await status("متوقف شد");
    const capped = await log(green, stepsRun);
    const exhausted = capped.filter(event => event.type === "budget.exhausted");
    assert.equal(exhausted.length, 1);
    assert.equal(exhausted[0].type === "budget.exhausted" ? exhausted[0].kind : null, "steps");
    assert.equal(exhausted[0].type === "budget.exhausted" ? exhausted[0].limit : null, 4);
    const last = capped.at(-1);
    assert.ok(last?.type === "run.finished" && last.status === "stopped", "the cap finished the run stopped");
    await expect(page.getByTestId("limit-steps")).toContainText("۴ از ۴");
    await shot("steps-cap-fa");
    evidence.push("S3 max_steps=4 stopped the run with budget.exhausted {steps, 4} then run.finished stopped");

    await configure({ verify: { max_steps: 40, max_minutes: 1 } });
    const timeRun = await start("demo verify slow");
    await status("متوقف شد");
    const timed = await log(green, timeRun);
    const timeExhausted = timed.filter(event => event.type === "budget.exhausted");
    assert.equal(timeExhausted.length, 1);
    assert.equal(timeExhausted[0].type === "budget.exhausted" ? timeExhausted[0].kind : null, "time");
    assert.ok(timed.some(event => event.type === "run.finished" && event.status === "stopped"));
    const orphans = childrenOf(app.process().pid!, ["ping.exe", "pytest.exe"]);
    assert.deepEqual(orphans, [], "no command process outlived the stopped run");
    assert.match(await readFile(join(green, "notes.txt"), "utf8"), /slow work/, "the edit stayed on disk");
    await shot("time-cap-fa");
    await configure({ verify: { max_minutes: 30 } });
    evidence.push("S3 max_minutes=1 stopped the run on the wall clock, the edit stayed and no command process survived");
  }

  if (wanted("S4")) {
    // S4: a real pytest renders read-only, and a hanging command shows the timeout variant.
    await api("/workspaces", "POST", { path: red });
    await page.reload();
    await expect(page.locator("#task")).toBeEnabled();
    const failRun = await start("demo verify fail");
    await status("پایان یافت");
    await expandAll();
    const failed = await log(red, failRun);
    const panel = page.getByTestId("terminal-panel").first();
    await expect(panel).toContainText("$ pytest -q");
    await expect(page.getByTestId("test-passed").first()).toContainText("۱۱ موفق");
    await expect(page.getByTestId("test-failed").first()).toContainText("۱ ناموفق");
    const exit = failed.find(event => event.type === "test.result");
    assert.ok(exit && exit.type === "test.result" && exit.exit_code === 1, "a real exit code was reported");
    assert.equal(await page.locator(".terminal-panel textarea, .terminal-panel [contenteditable]").count(), 0, "the terminal takes no input");
    await shot("terminal-fa");
    await expect(page.getByTestId("test-results").first()).toBeVisible();
    await shot("test-results-fa");

    await configure({ terminal: { timeout_seconds: 2 } }, red);
    const hangRun = await start("demo verify hang");
    await status("پایان یافت");
    await expandAll();
    await expect(page.getByTestId("timeout-card").first()).toBeVisible({ timeout: 60000 });
    await expect(page.locator(".terminal-timeout").first()).toContainText("پایان زمان");
    await shot("timeout-terminal-fa");
    const hung = await log(red, hangRun);
    const timed = hung.find(event => event.type === "tool.result" && /"timed_out":\s*true/.test(event.text));
    assert.ok(timed, "the command was killed by the workspace deadline");
    await page.getByTestId("timeout-retry").first().click();
    await expect(page.getByTestId("approval-card")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("approval-reject").click();
    await configure({ terminal: { timeout_seconds: 120 } }, red);
    evidence.push("S4 real pytest rendered read-only with ۱۱ موفق / ۱ ناموفق and a timeout variant with its kill note and retry approval");
    await api("/workspaces", "POST", { path: green });
    await page.reload();
    await expect(page.locator("#task")).toBeEnabled();
  }

  if (wanted("S5")) {
    // S5: the ring, its tooltip and the breakdown popover match the events they came from.
    const runId = await start("demo verify gate");
    await status("پایان یافت");
    const events = await log(green, runId);
    const context = events.filter(event => event.type === "context.updated" && event.scope.agent === "parent").at(-1);
    assert.ok(context && context.type === "context.updated" && context.context_window, "the run reported occupancy");
    const label = ringLabel(context.input_tokens, context.context_window ?? null, "fa", { used: context.estimated, window: context.context_window_estimated ?? false });
    const ring = page.getByTestId("context-ring");
    await expect(ring).toHaveAttribute("aria-label", `${label} زمینه استفاده شده`);
    const arc = arcDash(usedPercent(context.input_tokens, context.context_window ?? null));
    const offset = await page.locator(".ring-arc").evaluate(element => (element as SVGCircleElement).getAttribute("stroke-dashoffset"));
    assert.equal(Number(offset).toFixed(2), arc.dashoffset.toFixed(2));
    await ring.hover();
    await expect(page.locator(".tooltip").first()).toContainText(label);
    await shot("ring-tooltip-fa");
    await ring.click();
    await expect(page.locator(".context-popover")).toBeVisible();
    for (const row of ["messages", "tool_results", "system", "skills", "memory"]) await expect(page.getByTestId(`context-row-${row}`)).toBeVisible();
    await expect(page.getByTestId("context-total")).toContainText(compactTokens(context.input_tokens, "fa"));
    // The marker sits at the workspace's configured threshold, not at the mock's default.
    const threshold = (JSON.parse(await readFile(join(green, ".harness", "config.json"), "utf8")) as { context: { compaction_percent: number } }).context.compaction_percent;
    await expect(page.getByTestId("context-threshold")).toHaveAttribute("data-percent", String(threshold));
    await expect(page.getByTestId("context-new-chat")).toBeDisabled();
    await shot("breakdown-fa");
    await page.keyboard.press("Escape");
    await expect(page.locator(".context-popover")).toHaveCount(0);
    // Escape closes and hands focus back to the ring, so the keyboard keeps its place.
    await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute("data-testid")), { timeout: 5000 }).toBe("context-ring");
    evidence.push(`S5 ring ${label}, arc ${offset}, five rows, marker at ${percentLabel(threshold / 100, "fa")}, new chat disabled without a summary`);
  }

  if (wanted("S6")) {
    // S6: compaction fired for the seeded run and the handoff carries its summary.
    const task = page.locator(".task-link").filter({ hasText: "Seed the summary" });
    const history = page.locator(".workspace-history details").filter({ has: task });
    if (await history.getAttribute("open") === null) await history.locator("summary").click();
    await task.click();
    await expect(page.locator(".summary-notice").first()).toBeVisible({ timeout: 30000 });
    const seededEvents = await log(green, seeded.run_id);
    const summaries = seededEvents.filter(event => event.type === "context.summarized");
    // One notice per compaction operation: the 20K fixture window is small enough that this
    // long run compacts twice, so the count is asserted against the operations, not a magic 1.
    assert.ok(summaries.length >= 1, "the seeded run compacted its history");
    const operations = new Set(summaries.map(event => event.type === "context.summarized" && event.operation_id));
    assert.equal(operations.size, summaries.length, "every notice is a distinct operation");
    // The timeline renders one notice per operation, no more and no fewer.
    await expect(page.locator(".summary-notice")).toHaveCount(summaries.length);
    const summaryFile = await readFile(seeded.summary, "utf8");
    assert.ok(summaryFile.length > 0 && summaryFile.length <= 12_000, "the summary is bounded");
    assert.ok(!summaryFile.includes("INTERNAL"), "no internal marker leaked");
    await shot("compaction-fa");
    const ring = page.getByTestId("context-ring");
    await ring.click();
    const newChat = page.getByTestId("context-new-chat");
    await expect(newChat).toBeEnabled();
    const created = page.waitForResponse(response => new URL(response.url()).pathname === "/runs" && response.request().method() === "POST");
    await newChat.click();
    const handoff = (await (await created).json() as { run_id: string }).run_id;
    await expect(page.locator("#task")).toBeEnabled();
    const request = JSON.parse(await readFile(join(green, ".harness", "runs", handoff, "request.json"), "utf8")) as { task: string; seed_summary_from?: string };
    assert.equal(request.seed_summary_from, seeded.run_id);
    assert.match(request.task, /Previous conversation summary/);
    assert.match(request.task, /Earlier work on the invoice parser/);
    await shot("handoff-fa");
    await status("پایان یافت");
    evidence.push(`S6 ${summaries.length} distinct context.summarized operation(s) rendered one notice each, summary ${seeded.bytes} bytes on disk, the next run's request.json carries the block from ${seeded.run_id}`);
  }

  if (wanted("S7")) {
    // S7: the context settings match the mock, save behind approval, and survive a reload.
    await openSettings(3);
    await expect(page.getByTestId("context-window")).toHaveText("خودکار");
    await expect(page.getByTestId("context-percent-value")).toHaveText("۶۰٪");
    await expect(page.getByTestId("context-keep")).toHaveValue("۸");
    await expect(page.getByTestId("context-offload")).toHaveAttribute("aria-checked", "true");
    await expect(page.getByTestId("context-ring-switch")).toHaveAttribute("aria-checked", "true");
    await expect(page.getByTestId("verify-steps")).toHaveValue("۴۰");
    await shot("settings-context-fa");
    await page.getByTestId("context-percent").fill("45");
    await expect(page.getByTestId("context-percent-value")).toHaveText("۴۵٪");
    await page.getByTestId("verify-save").click();
    await expect(page.locator(".verify-settings .approval-card")).toBeVisible();
    await page.getByTestId("approval-approve").click();
    await expect(page.getByTestId("context-percent-value")).toHaveText("۴۵٪", { timeout: 30000 });
    const saved = JSON.parse(await readFile(join(green, ".harness", "config.json"), "utf8")) as { context: { compaction_percent: number } };
    assert.equal(saved.context.compaction_percent, 45);
    await page.reload();
    await expect(page.locator("#task")).toBeEnabled({ timeout: 60000 });
    await openSettings(3);
    await expect(page.getByTestId("context-percent-value")).toHaveText("۴۵٪");
    await page.getByTestId("context-percent").fill("75");
    await page.getByTestId("verify-save").click();
    await expect(page.locator(".verify-settings .approval-card")).toBeVisible();
    await page.getByTestId("approval-reject").click();
    await expect(page.getByTestId("context-percent-value")).toHaveText("۴۵٪", { timeout: 30000 });
    const rejected = JSON.parse(await readFile(join(green, ".harness", "config.json"), "utf8")) as { context: { compaction_percent: number } };
    assert.equal(rejected.context.compaction_percent, 45);
    evidence.push("S7 context settings matched the mock, saved 45 behind approval, survived a reload, and a rejected save kept 45");
  }

  if (wanted("S8")) {
    // S8: the terminal settings match the mock and the deadline they set is the one commands get.
    await openSettings(4);
    await expect(page.getByTestId("terminal-shell")).toHaveValue("auto");
    await expect(page.getByTestId("terminal-timeout")).toHaveValue("۱۲۰");
    await expect(page.getByTestId("terminal-lines")).toHaveValue("۲۰۰");
    await expect(page.getByTestId("terminal-env")).toHaveText("قفل · ثابت");
    await expect(page.locator(".verify-row").filter({ has: page.getByTestId("terminal-env") }).locator("input")).toHaveCount(0);
    await expect(page.getByTestId("test-mode-auto")).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("test-detected")).toHaveText("pytest -q");
    await expect(page.locator(".verify-row").filter({ has: page.getByTestId("test-detected") })).toContainText("از pyproject.toml");
    await expect(page.getByTestId("verify-gate")).toHaveAttribute("aria-checked", "true");
    await shot("settings-terminal-fa");
    await page.getByTestId("terminal-timeout").fill("30");
    await page.getByTestId("verify-save").click();
    await expect(page.locator(".verify-settings .approval-card")).toBeVisible();
    await page.getByTestId("approval-approve").click();
    await expect(page.getByTestId("terminal-timeout")).toHaveValue("۳۰", { timeout: 30000 });
    const runId = await start("demo verify gate");
    await status("پایان یافت");
    const events = await log(green, runId);
    const command = events.find(event => event.type === "tool.result" && /"command": "pytest -q"/.test(event.text));
    assert.ok(command && command.type === "tool.result", "the check ran");
    assert.match(command.type === "tool.result" ? command.text : "", /"timeout_seconds": 30/, "the workspace deadline reached the runner");
    evidence.push("S8 terminal settings matched the mock; the saved 30 s deadline is the one the next command ran with");

    await openSettings(4);
    await page.getByTestId("verify-gate").click();
    await page.getByTestId("verify-save").click();
    await expect(page.locator(".verify-settings .approval-card")).toBeVisible();
    await page.getByTestId("approval-approve").click();
    await expect(page.getByTestId("verify-gate")).toHaveAttribute("aria-checked", "false", { timeout: 30000 });
    const unguarded = await start("demo verify gate");
    await status("پایان یافت");
    const unguardedEvents = await log(green, unguarded);
    assert.equal(unguardedEvents.filter(event => event.type === "verify.required").length, 0, "a disabled gate never blocks");
    assert.ok(unguardedEvents.some(event => event.type === "tool.call" && event.name === "write_file"));
    await openSettings(4);
    await page.getByTestId("verify-gate").click();
    await page.getByTestId("verify-save").click();
    await expect(page.locator(".verify-settings .approval-card")).toBeVisible();
    await page.getByTestId("approval-approve").click();
    await expect(page.getByTestId("verify-gate")).toHaveAttribute("aria-checked", "true", { timeout: 30000 });
    evidence.push("S8 turning the gate off let a scripted edit finish without a single verify.required");
  }

  if (wanted("S9")) {
    // S9: the same surfaces in English at both widths, with no overflow and mirrored layout.
    await openSettings(3);
    await page.locator(".settings-nav button").nth(1).click();
    await page.getByRole("button", { name: "English", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
    await page.locator(".settings-nav button").nth(3).click();
    // Whatever the earlier scenarios stored is what English must render, in Latin digits.
    const stored = (JSON.parse(await readFile(join(green, ".harness", "config.json"), "utf8")) as { context: { compaction_percent: number } }).context.compaction_percent;
    await expect(page.getByTestId("context-percent-value")).toHaveText(`${stored}٪`);
    await shot("settings-context-en");
    await page.locator(".settings-nav button").nth(4).click();
    await expect(page.getByTestId("test-detected")).toHaveText("pytest -q");
    await shot("settings-terminal-en");
    await page.setViewportSize({ width: 760, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await shot("settings-terminal-en-narrow");
    await page.setViewportSize({ width: 1440, height: 900 });
    const task = page.locator(".task-link").filter({ hasText: "Seed the summary" });
    const history = page.locator(".workspace-history details").filter({ has: task });
    if (await history.getAttribute("open") === null) await history.locator("summary").click();
    await task.click();
    await expect(page.getByTestId("context-ring")).toBeVisible();
    const label = await page.getByTestId("context-ring").getAttribute("aria-label");
    assert.match(label ?? "", /^[0-9]+٪ · /, "English digits in the ring label");
    await page.getByTestId("context-ring").click();
    await expect(page.locator(".context-popover")).toBeVisible();
    await shot("breakdown-en");
    await page.keyboard.press("Escape");
    await page.setViewportSize({ width: 760, height: 900 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await shot("ring-en-narrow");
    await page.setViewportSize({ width: 1440, height: 900 });
    // The exhausted card in English, then declined so the run ends without another fix cycle.
    await api("/workspaces", "POST", { path: red });
    await page.reload();
    await expect(page.locator("#task")).toBeEnabled({ timeout: 60000 });
    await start("demo verify budget");
    await expect(page.locator(".compose-region .question-exhausted")).toBeVisible({ timeout: 120000 });
    await expect(page.locator(".compose-region .question-exhausted")).toContainText("3 unsuccessful attempts");
    await shot("exhausted-retry-en");
    await page.locator(".question-decline").click();
    await status("Completed");
    evidence.push("S9 both settings screens, the ring and the exhausted card render in English at 1440 and 760 with no horizontal overflow");
  }

  assert.deepEqual(errors, []);
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({ passed: true, evidence, facts, errors }, null, 2));
  console.log("Phase 7 walkthrough passed", evidence);
} catch (error) {
  await shot("failure");
  await writeFile(join(artifacts, "evidence.json"), JSON.stringify({ passed: false, evidence, facts, errors, failure: String(error) }, null, 2));
  throw error;
} finally {
  await app.close();
}
