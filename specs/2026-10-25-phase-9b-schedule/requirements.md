# Phase 9b: Schedule. Requirements

## Goal
Scheduled tasks that respect human-in-the-loop even when nobody is watching. A scheduler inside the engine that runs
only while the app is open, a Schedule screen that lists and edits what is scheduled, an add dialog whose two
permission controls resolve to the stricter one, and a missed run that is *offered* rather than silently started.

## In scope
- `backend/scheduling/` — the schedule record, recurrence math as a pure function, the ticker, missed-run detection,
  and run creation through the existing `RunManager` (no second execution path).
- App-data persistence for schedules, with a reload that recomputes the next occurrence.
- Routes `GET/POST /schedules`, `PUT/DELETE /schedules/{id}`, `POST /schedules/{id}/run`,
  `POST /schedules/{id}/skip` — the four the tech stack already promises plus the two the mock's row needs.
- `Schedule.dc.html` and `ScheduleAdd.dc.html` rebuilt in React: header, active rows, template grid, add/edit dialog.
- The `noSchedules` empty state wired to the screen, and the sidebar's Schedule item made real.
- `src/i18n/schedule.ts` (fa/en, one shape), `src/lib/schedule.ts` (pure helpers), `src/lib/use-schedules.ts` (hook),
  `tests/unit/schedule.test.ts`, and a `tests/phase9b-desktop.ts` walkthrough.

## Out of scope
- A background service, a tray-resident scheduler, Windows Task Scheduler, or anything that runs while the app is
  closed. This is the phase's central promise, not a limitation to fix later.
- Cron expressions, intervals shorter than a day, multi-day recurrences, per-schedule rules files.
- Notifications outside the app (toasts, OS notifications, email).
- Automatically running a missed schedule.
- Changing the permission middleware, the always-ask list, or the plan/verify gates.

## Functional requirements

### Scheduling
- **R1 Recurrence is a pure function.** `next_run_after(schedule, now)` returns the first occurrence **strictly
  after** `now`: daily at 02:00 asked at 01:00 today is today 02:00; asked at exactly 02:00:00 it is tomorrow 02:00;
  weekly Friday 09:00 asked on Wednesday is that Friday, asked on Friday at 09:00:00 is the next Friday.
  `repeat` is `daily` or `weekly` (weekly carries `weekday`, Monday = 0); `time` is local `HH:MM`, 24-hour.
- **R2 Validity bounds recurrence.** `valid_until` is a local date or `None` for long-term, inclusive: a 09:00 run on
  the until date still happens. Past the last occurrence `next_run_at` is `null`, the row reads as expired, and the
  schedule is kept rather than deleted.
- **R3 Schedules live in app data.** They persist in the app-data catalog beside models, settings and tasks, never in
  the workspace's `.harness/`. A restart reloads them and recomputes `next_run_at` from the recurrence.
- **R4 The ticker runs only while the engine is alive.** It wakes on a fixed interval, uses an injectable clock, and
  starts one run per due schedule. A run that is still executing never blocks a different schedule from starting: an
  unattended run paused on an approval must not starve the queue.
- **R5 A due schedule becomes an ordinary run.** `RunRequest{task: prompt, workspace, model, mode: effective,
  schedule_id}` goes through the same `RunManager.start` as the composer. Its events are that run's own
  `events.jsonl`, a `TaskRecord` with `schedule_id` appears under its workspace, and the approvals it raises are the
  ordinary inbox approvals.
- **R6 The stricter of mode and access ceiling applies.** `mode` is read-only / ask / auto; `ceiling` is `report`
  (read-only and report) or `full`. `report` forces read-only; `full` leaves the mode. Six cells, one table, applied
  in the engine when the run is created so the middleware, the plan gate and the verify gate all see the effective
  mode.
- **R7 The unattended default is read-only + report.** The dialog opens on those two values.
- **R8 Full access never bypasses the always-ask list.** A scheduled run in auto still escalates web search, engine
  storage, rules-file edits and high-risk commands to an approval, because that escalation lives in the permission
  middleware and a schedule is a normal run.
- **R9 A scheduled run that needs approval pauses, and the row says so.** The row shows the number of pending
  approvals belonging to that schedule's runs; the run resumes when the person answers in the inbox.
- **R10 A missed run is offered, never started.** On startup and on each tick, a schedule whose persisted
  `next_run_at` is in the past becomes `missed` with the time it was due and its `next_run_at` advances. Nothing
  runs by itself. "Run now" starts exactly one run and clears `missed`; "skip" clears it and starts nothing. After
  any start, the next occurrence is computed from *now*, so a slow run or a long sleep never produces a burst.
- **R11 Enable/disable is immediate and persistent.** A disabled schedule never starts a run and keeps its next
  occurrence; the row shows it as paused.
- **R12 A schedule that cannot run says why.** A missing or unusable model, a workspace that moved or was deleted,
  or an unreadable rules file leaves `last_error` on the row and starts nothing; the next tick retries once the
  cause is fixed. A schedule never fails silently and never retries in a tight loop.

### Screen
- **R13 The page matches `Schedule.dc.html`.** Title `کارهای زمانبندیشده`, the mock's two-sentence subtitle, a "new"
  button, a group label with a count, one row per schedule (clock icon, title, `workspace · recurrence`, mode chip,
  last result or the queued-approval count, an on/off switch, a more menu), then the template grid under
  `این کارهای پرکاربرد را امتحان کن`. The chip's tone follows the mode — neutral for read-only, accent for ask,
  danger for auto — because auto is the one that can change files without a person in the room.
- **R14 The dialog matches `ScheduleAdd.dc.html`.** Name, prompt box (with the improve-text button and the mode chip
  inside it), workspace, access-ceiling chip, the red warning when full access is chosen, Repeat, Time, Validity,
  Cancel, Confirm. Confirm is disabled while the name or prompt is empty. The same dialog edits an existing schedule,
  prefilled.
- **R15 Six templates.** Nightly tests, daily git review, weekly dependency check, test coverage, TODO cleanup,
  weekly summary — each with the mock's title and prompt text. A click opens the dialog prefilled (name, prompt,
  recurrence, read-only + report); nothing is created until Confirm.
- **R16 The empty state is wired.** `EmptyState` with `statesCopy(locale).noSchedules`, whose help text no longer
  claims there is no scheduler and whose primary action opens the dialog. `WIRED.noSchedules` becomes `"schedule"`.
- **R17 The sidebar's Schedule item is real.** It links to `/schedule/`, marks itself active, and loses the "later
  phase" tooltip.
- **R18 The more menu offers Edit, Run now and Delete.** Delete asks once and names what is lost: the schedule
  itself. Runs it already produced stay as tasks under the workspace.
- **R19 Every string is in `fa` and `en` with one shape.** Counts and clock times use Persian digits in Persian;
  workspace paths and anything code-like stay LTR.
- **R20 Accessibility follows the existing contracts.** The switch is `role="switch"` with `aria-checked` and a
  label naming the schedule; the dialog is `role="dialog"` with a label, Escape closes it through the shortcuts
  table's `dialog` scope, focus lands inside it; templates and rows are buttons, not links with no destination.

## Non-functional
- Gates stay green: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`, `npm run test:ui`, `npm run build`,
  `npm run build:electron`, `npm run test:desktop`.
- No scheduler library. The engine already owns one event loop; the ticker is a task in the app lifespan and the
  recurrence is a pure function, so both are testable without a running clock.
- The scheduler does no work at import time and nothing when the engine is not running.
- Schedules hold user text (name, prompt) in app data, where task titles already live. No secrets, no keys, no
  tokens, and nothing about a schedule is written into the workspace.
- Generated wire types only: the new records join the `Protocol` envelope and `npm run generate:protocol` produces
  the TypeScript. No hand-written duplicate.

## Decisions
- **D34 Schedules persist in the app-data catalog, not a new `app.sqlite`.** The tech stack names
  `%APPDATA%/CodeHarness/app.sqlite`, but this product has no such file: models, settings and tasks live in
  `catalog.json` behind one atomic write and one lock, and the Data screen already reports that folder as the app
  data (`DataSummary.app_data`). Adding a second store would mean two things to back up, two to clear and two to
  migrate. **This changes a constitution line and needs approval.**
- **D35 An asyncio ticker, not APScheduler.** The brief offers APScheduler as an example. A dependency that brings
  its own thread pool and its own persistence, to run work that must stop when the process stops, buys nothing here;
  a ~40-line task plus a pure `next_run_after` is smaller, testable with a fixed clock, and cannot outlive the app.
- **D36 A missed run is a row, not a run.** The app cannot know whether the machine slept, the person was away, or
  the workspace moved. Starting unattended work the moment the window opens would queue approvals before anyone has
  looked at anything. It is offered.
- **D37 `min(mode, ceiling)` is applied at run creation.** One place, in the engine, before `RunRequest` exists — so
  no later layer has to remember the ceiling, and a schedule cannot widen its own permission by being edited while a
  run is queued.
- **D38 `schedule_id` on the request and on the task record.** That single link makes "N approvals queued", "which
  schedule made this" and the row's last result answerable from what is already persisted, with no second ledger.
- **D39 Creating a schedule needs no inbox approval.** It is the person's own action on their own app, like changing
  a setting; an approval they raise for themselves is approving themselves (the reasoning behind D32). Full access
  is the exception that stays visible: a red warning and an explicit choice, not a silent default.
- **D40 Every due schedule starts its own run; there is no global cap.** A run paused on an approval must not hold
  the queue, and the inbox is already built to hold several pending approvals at once.
- **D41 A paused group sits under the active one.** The mock draws only `فعال (۲)`; a switched-off schedule has to
  appear somewhere, so a second group renders when it is not empty. An extension, not a contradiction.
- **D42 The six-cell table exists twice, and both are tested.** The dialog has to answer before a round trip and the
  engine has to answer when a run starts, so `effectiveMode` is a three-line helper on each side with the same table
  in a test on each side. The engine's answer is authoritative; the dialog's is a display of it.

## Open questions
Two places where following the mock exactly would contradict the rest of the product. Both need an answer before
Step 6.
- **Q1 The queued-approval text is green in the mock** (`#86EFAC`, the same colour as "last run: success"). Everywhere
  else, something waiting on a person is amber: the inbox badge, the task dot, the "needs you" panel. Recommend
  amber for the queued-approval text and green only for a successful last run; that is the one deliberate colour
  change from the mock.
- **Q2 Time is drawn as a dropdown-style button** (`ساعت: ۰۲:۰۰` with a caret). A menu of times cannot offer every
  minute, and a native `<input type="time">` styled to look like that button gives any minute, the OS picker and
  keyboard entry for free. Recommend the native input with the mock's appearance; the caret becomes decorative.
