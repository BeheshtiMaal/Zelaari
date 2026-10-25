import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { _electron as electron, expect, type ElectronApplication, type Page } from "@playwright/test";

/**
 * The Phase 9b walkthrough.
 *
 * Four claims from `requirements.md`, each turned into something the machine can check:
 * a schedule created in the dialog is a row that says when it will next run (R1, R3); it
 * survives a restart with a recomputed occurrence (R4); switching it off moves it to the
 * paused group and deleting it returns the empty state (R6); and an occurrence that fell due
 * while the app was closed is *offered*, with nothing started until a person says so (R12).
 *
 * Screenshots are evidence, not the assertion.
 */

const root = process.cwd();
const artifacts = resolve(root, "artifacts");
await mkdir(artifacts, { recursive: true });
const profile = await mkdtemp(resolve(tmpdir(), "codeharness-phase9b-"));
const catalogFile = resolve(profile, "catalog.json");
const evidence: Record<string, unknown> = {};

// The app gives the engine thirty seconds to answer, and a cold `import server.app` costs
// about a minute on a cold disk cache — the interpreter is warmed here, outside that budget,
// so a slow disk is not mistaken for a broken engine. Eight seconds once warm.
const python = resolve(root, "backend/.venv/Scripts/python.exe");
execFileSync(python, ["-c", "import server.app"], { cwd: resolve(root, "backend"), stdio: "ignore" });

interface StoredSchedule {
  id: string;
  name: string;
  mode: string;
  ceiling: string;
  next_run_at: string | null;
  last_run_at: string | null;
  last_status: string | null;
  last_run_id: string | null;
  missed_at: string | null;
  enabled: boolean;
  [key: string]: unknown;
}

async function launch(userData = profile): Promise<ElectronApplication> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value && key !== "ELECTRON_RUN_AS_NODE" && !key.endsWith("API_KEY") && !key.startsWith("LANGSMITH_") && !key.startsWith("LANGCHAIN_")) env[key] = value;
  }
  // Persian throughout: the digits and the RTL layout are part of what is being checked.
  return electron.launch({ args: [root], env: { ...env, CODEHARNESS_LANGUAGE: "fa", CODEHARNESS_TEST_USER_DATA: userData, CODEHARNESS_PACKAGED_ENGINE: "0" }, timeout: 120000 });
}

async function ready(app: ElectronApplication): Promise<Page> {
  const page = await app.firstWindow();
  page.setDefaultTimeout(30000);
  await expect(page.locator(".app-shell")).toHaveAttribute("data-ready", "true", { timeout: 60000 });
  return page;
}

/** The schedule screen is a route of its own, so getting there is a navigation. */
async function openSchedule(page: Page): Promise<void> {
  // A relaunch does not always restore the last workspace, and a schedule needs one to
  // exist at all: the sample project is what the empty state offers.
  if (await page.getByTestId("state-sample-project").isVisible().catch(() => false)) {
    await page.getByTestId("state-sample-project").click();
    await expect(page.getByTestId("state-sample-project")).toBeHidden({ timeout: 60000 });
  }
  await page.locator('a[href="/schedule/"]').click();
  await expect(page.getByTestId("schedule-screen")).toBeVisible({ timeout: 60000 });
}

/** The engine's schedule times are naive local wall clock, so compare in the same shape. */
function localStamp(at: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}:${pad(at.getSeconds())}`;
}

async function readSchedules(): Promise<StoredSchedule[]> {
  const catalog = JSON.parse(await readFile(catalogFile, "utf8")) as { schedules?: StoredSchedule[] };
  return catalog.schedules ?? [];
}

/** The row's own test id carries the id the engine assigned, which is what the rest needs. */
async function rowId(page: Page): Promise<string> {
  const id = await page.locator("[data-testid^='schedule-row-']").first().getAttribute("data-testid");
  assert.ok(id, "there should be a row");
  return id.replace("schedule-row-", "");
}

// ── S1–S3: create, restart, pause, delete ────────────────────────────────────────────────
const first = await launch();
let scheduleId = "";
try {
  const page = await ready(first);
  await openSchedule(page);

  // S1: nothing scheduled yet, and the empty state offers the one action that fixes it.
  await expect(page.getByTestId("state-no-schedules")).toBeVisible({ timeout: 30000 });
  const emptyText = await page.getByTestId("state-no-schedules").innerText();
  assert.ok(emptyText.length > 0, "the empty state has something to say");
  await page.screenshot({ path: resolve(artifacts, "phase9b-s1-empty.png") });

  // S2: the dialog opens on the name field, and refuses to confirm an empty schedule.
  await page.getByTestId("state-add-schedule").click();
  await expect(page.getByTestId("schedule-dialog")).toBeVisible();
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("data-testid"));
  assert.equal(focused, "schedule-name", "focus lands on the name field");
  await expect(page.getByTestId("schedule-confirm")).toBeDisabled();

  await page.getByTestId("schedule-name").fill("اجرای شبانه‌ی تست‌ها");
  await page.getByTestId("schedule-prompt").fill("هر شب تست‌ها را اجرا کن و علت شکست‌ها را گزارش بده");

  // The two permission controls, and the stricter of them winning (R5, R7). Three moves, one
  // per direction the table can go: a ceiling that cannot upgrade, a mode that reaches the
  // ceiling, and a ceiling that tightens a looser mode.
  await expect(page.getByTestId("schedule-effective")).toHaveText("حالت اجرا: فقط خواندن");
  await page.getByTestId("schedule-ceiling").selectOption("full");
  await expect(page.getByTestId("schedule-full-warning")).toBeVisible();
  await expect(page.getByTestId("schedule-effective")).toHaveText("حالت اجرا: فقط خواندن");
  await page.screenshot({ path: resolve(artifacts, "phase9b-s2-full-warning.png") });

  await page.getByTestId("schedule-mode").selectOption("ask");
  await expect(page.getByTestId("schedule-effective")).toHaveText("حالت اجرا: با تأیید");

  await page.getByTestId("schedule-ceiling").selectOption("report");
  await expect(page.getByTestId("schedule-effective")).toHaveText("حالت اجرا: فقط خواندن");
  await expect(page.getByTestId("schedule-full-warning")).toHaveCount(0);

  // Keep the ask mode with a full ceiling, so the row below has something to disagree about.
  await page.getByTestId("schedule-ceiling").selectOption("full");
  await expect(page.getByTestId("schedule-effective")).toHaveText("حالت اجرا: با تأیید");
  evidence["s2-ceiling"] = await page.getByTestId("schedule-effective").innerText();

  await page.getByTestId("schedule-repeat").selectOption("daily");
  await page.getByTestId("schedule-time").fill("09:30");
  await page.getByTestId("schedule-confirm").click();
  await expect(page.getByTestId("schedule-dialog")).toBeHidden({ timeout: 30000 });

  // S3: the row says what it is, how it is allowed to act, and when it runs next.
  scheduleId = await rowId(page);
  const row = page.getByTestId(`schedule-row-${scheduleId}`);
  await expect(row).toContainText("اجرای شبانه‌ی تست‌ها");
  await expect(page.getByTestId(`schedule-mode-${scheduleId}`)).toHaveText("با تأیید");
  await expect(page.getByTestId(`schedule-result-${scheduleId}`)).toHaveText("هنوز اجرا نشده");
  const next = await page.getByTestId(`schedule-next-${scheduleId}`).innerText();
  assert.match(next, /اجرای بعدی/, `the row should say when it runs next: ${next}`);
  assert.match(next, /[۰-۹]/, `the next-run time should use Persian digits: ${next}`);
  assert.match(await row.innerText(), /هر شب ساعت ۰۹:۳۰/, "the recurrence is written the way the mock writes it");
  evidence["s3-row"] = { id: scheduleId, next, text: await row.innerText() };
  await page.screenshot({ path: resolve(artifacts, "phase9b-s3-row.png") });

  // It is app data: the schedule is in the catalog and nowhere near the workspace.
  const stored = await readSchedules();
  assert.equal(stored.length, 1, "one schedule is stored");
  assert.equal(stored[0].id, scheduleId);
  assert.ok(stored[0].next_run_at, "a created schedule has a next occurrence");
  assert.equal(stored[0].mode, "ask", "the mode is stored as it was chosen");
  assert.equal(stored[0].ceiling, "full", "and so is the ceiling");
  evidence["s3-stored"] = { next_run_at: stored[0].next_run_at, mode: stored[0].mode, ceiling: stored[0].ceiling, enabled: stored[0].enabled };
} finally {
  await first.close();
}

// ── S4: the same profile, a recomputed occurrence, a pause and a delete ──────────────────
const second = await launch();
try {
  const page = await ready(second);
  await openSchedule(page);

  // S4a: still there, with an occurrence the reload computed rather than one it trusted.
  const row = page.getByTestId(`schedule-row-${scheduleId}`);
  await expect(row).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("state-no-schedules")).toHaveCount(0);
  await expect(page.getByTestId(`schedule-next-${scheduleId}`)).toContainText("اجرای بعدی");
  const afterRestart = (await readSchedules())[0];
  assert.equal(afterRestart.id, scheduleId, "the same schedule, not a copy");
  assert.ok(afterRestart.next_run_at, "the reload computed a next occurrence");
  assert.ok(afterRestart.next_run_at > localStamp(new Date()), `the next occurrence is in the future: ${afterRestart.next_run_at}`);
  evidence["s4-after-restart"] = afterRestart.next_run_at;
  await page.screenshot({ path: resolve(artifacts, "phase9b-s4-restarted.png") });

  // S4b: editing is where the two permissions can be pulled apart after the fact. Dropping the
  // ceiling to report has to change what the row claims, not just what is stored.
  await page.getByTestId(`schedule-more-${scheduleId}`).click();
  await page.getByTestId(`schedule-edit-${scheduleId}`).click();
  await expect(page.getByTestId("schedule-dialog")).toBeVisible();
  await expect(page.getByTestId("schedule-name")).toHaveValue("اجرای شبانه‌ی تست‌ها");
  await expect(page.getByTestId("schedule-mode")).toHaveValue("ask");
  await page.getByTestId("schedule-ceiling").selectOption("report");
  await expect(page.getByTestId("schedule-effective")).toHaveText("حالت اجرا: فقط خواندن");
  await page.getByTestId("schedule-confirm").click();
  await expect(page.getByTestId("schedule-dialog")).toBeHidden({ timeout: 30000 });
  await expect(page.getByTestId(`schedule-mode-${scheduleId}`)).toHaveText("فقط خواندن", { timeout: 30000 });
  assert.equal((await readSchedules())[0].ceiling, "report", "the tighter ceiling is persisted");
  assert.equal((await readSchedules())[0].mode, "ask", "and the chosen mode is untouched");
  evidence["s4-edited"] = await page.getByTestId(`schedule-mode-${scheduleId}`).innerText();
  await page.screenshot({ path: resolve(artifacts, "phase9b-s4-edited.png") });

  // S4c: off is a group, not a deletion.
  await page.getByTestId(`schedule-switch-${scheduleId}`).click();
  await expect(row).toHaveClass(/paused/, { timeout: 30000 });
  await expect(page.locator(".schedule-group").filter({ hasText: "غیرفعال" })).toBeVisible();
  assert.equal((await readSchedules())[0].enabled, false, "the pause is persisted");
  await page.screenshot({ path: resolve(artifacts, "phase9b-s4-paused.png") });

  // And back on, so the delete below is not the only way out.
  await page.getByTestId(`schedule-switch-${scheduleId}`).click();
  await expect(row).not.toHaveClass(/paused/, { timeout: 30000 });
  assert.equal((await readSchedules())[0].enabled, true, "switching back on is persisted too");

  // S4d: delete names the loss, then the empty state comes back.
  await page.getByTestId(`schedule-more-${scheduleId}`).click();
  await page.getByTestId(`schedule-delete-${scheduleId}`).click();
  await expect(page.getByTestId("schedule-delete-dialog")).toBeVisible();
  const confirmText = await page.getByTestId("schedule-delete-dialog").innerText();
  assert.match(confirmText, /فضای کاری/, `the confirmation says what survives: ${confirmText}`);
  await page.screenshot({ path: resolve(artifacts, "phase9b-s4-delete.png") });
  await page.getByTestId("schedule-delete-confirm").click();
  await expect(page.getByTestId("schedule-delete-dialog")).toBeHidden({ timeout: 30000 });
  await expect(page.getByTestId("state-no-schedules")).toBeVisible({ timeout: 30000 });
  assert.equal((await readSchedules()).length, 0, "the schedule is gone from the catalog");
} finally {
  await second.close();
}

// ── S5: an occurrence that fell due while the app was closed is offered, not started ─────
const third = await launch();
try {
  const page = await ready(third);
  await openSchedule(page);
  // Create one, so the overdue record below is a real one rather than a hand-built one.
  await page.getByTestId("state-add-schedule").click();
  await page.getByTestId("schedule-name").fill("گزارش شبانه");
  await page.getByTestId("schedule-prompt").fill("گزارش کوتاهی از وضعیت پروژه بنویس");
  await page.getByTestId("schedule-confirm").click();
  await expect(page.getByTestId("schedule-dialog")).toBeHidden({ timeout: 30000 });
  const id = await rowId(page);
  evidence["s5-created"] = id;
} finally {
  await third.close();
}

// With the app closed, move the occurrence into the past: this is what a night with the
// laptop shut looks like, and the engine has to be able to tell the difference between that
// and a schedule that is simply due.
const catalog = JSON.parse(await readFile(catalogFile, "utf8")) as { schedules: StoredSchedule[] };
const overdue = localStamp(new Date(Date.now() - 3 * 60 * 60 * 1000));
catalog.schedules[0].next_run_at = overdue;
catalog.schedules[0].missed_at = null;
catalog.schedules[0].last_run_at = null;
catalog.schedules[0].last_status = null;
catalog.schedules[0].last_run_id = null;
await writeFile(catalogFile, JSON.stringify(catalog, null, 2), "utf8");

const fourth = await launch();
try {
  const page = await ready(fourth);
  await openSchedule(page);
  const id = catalog.schedules[0].id;

  // The ticker sees it within one pass and the screen refreshes; the prompt is the offer.
  await expect(page.getByTestId(`schedule-missed-${id}`)).toBeVisible({ timeout: 90000 });
  const offer = await page.getByTestId(`schedule-missed-${id}`).innerText();
  assert.match(offer, /قرار بود ساعت/, `the offer names when it was due: ${offer}`);
  assert.match(offer, /همین حالا اجرا کن/, "the offer has a run-now answer");
  await expect(page.getByTestId(`schedule-result-${id}`)).toHaveText("زمان اجرا گذشته و برنامه بسته بود");

  // The claim that matters: it was offered, so nothing started by itself.
  const offered = (await readSchedules())[0];
  assert.ok(offered.missed_at, "the occurrence is recorded as missed");
  assert.equal(offered.last_run_id, null, "nothing ran on its own");
  assert.equal(offered.last_run_at, null, "and no run is attributed to the schedule");
  evidence["s5-offer"] = { missed_at: offered.missed_at, last_run_id: offered.last_run_id, text: offer };
  await page.screenshot({ path: resolve(artifacts, "phase9b-s5-missed.png") });

  // "Run now" is the person answering, and only then does a run exist.
  await page.getByTestId(`schedule-missed-run-${id}`).click();
  await expect.poll(async () => (await readSchedules())[0].last_run_id, { timeout: 60000 }).not.toBeNull();
  const started = (await readSchedules())[0];
  assert.ok(started.last_run_id, "run now starts exactly the run it says it started");
  evidence["s5-run"] = { last_run_id: started.last_run_id, missed_at: started.missed_at };
  await page.screenshot({ path: resolve(artifacts, "phase9b-s5-ran.png") });
} finally {
  await fourth.close();
}

console.log("Phase 9b walkthrough S1–S5 passed.");
console.log(JSON.stringify(evidence, null, 2));
