# Phase 9b: Schedule. Plan

Work top to bottom. One commit per step, tests written with the behaviour they describe. Do not start a step until the
previous one is green.

## Step 1: The schedule record and the recurrence math
Pure Python, no I/O, no clock.
- `backend/scheduling/model.py`:
  - `Repeat = Literal["daily", "weekly"]`, `Mode = Literal["read-only", "ask", "auto"]`,
    `Ceiling = Literal["report", "full"]`.
  - `ScheduleRecord`: `id`, `name`, `prompt`, `workspace`, `model`, `mode`, `ceiling`, `repeat`, `weekday`
    (`int | None`, validated to 0–6 when weekly), `time` (`HH:MM`, validated), `valid_until` (`date | None`,
    `None` = long-term), `enabled`, `created_at`, `next_run_at`, `last_run_at`, `last_status`, `last_run_id`,
    `missed_at`, `last_error`.
  - `next_run_after(schedule, now) -> datetime | None` — strictly after `now`, respecting weekday and validity.
  - `effective_mode(mode, ceiling) -> Mode` — the six-cell table.
  - `is_due(schedule, now) -> bool`, `mark_started`, `mark_finished`, `mark_missed` as small pure transitions so the
    ticker has no state of its own.
- `backend/tests/test_schedule_math.py`: daily and weekly boundaries (including exactly-on-the-minute), weekday
  wrap-around, the until-date inclusivity and expiry, a DST-shaped local-time case recorded as a known limitation,
  and the full six-cell matrix.

Commit: `feat(schedule): recurrence as a pure function and the six-cell permission table`

## Step 2: Persistence on the app-data catalog
- `CatalogData.schedules: list[ScheduleRecord]` (default empty, so an existing `catalog.json` loads unchanged).
- `backend/store/schedules.py`: `list_schedules`, `add_schedule`, `update_schedule`, `delete_schedule`,
  `find_schedule`, `reload` — each taking the catalog lock, persisting atomically, and recomputing `next_run_at`
  from the current time.
- `backend/tests/test_schedule_store.py`: create → reload from the same file → identical record and a recomputed
  next occurrence; a schedule in the catalog is absent from `.harness/`; a corrupt or missing record is skipped, not
  fatal.

Commit: `feat(schedule): schedules persist in app data and survive a restart`

## Step 3: The ticker, missed runs, and real runs
- `RunRequest.schedule_id: str | None`; `TaskRecord.schedule_id: str | None`; `bridge._start` copies it onto the
  task record; the projection keeps writing `request.json` (the audit artefact now says which schedule asked).
- `backend/scheduling/ticker.py`: `Scheduler(catalog, start, clock)` where `start` is an injected
  `Callable[[RunRequest], Awaitable[str]]`.
  - `tick()`: for each enabled schedule — mark missed if overdue, skip when not due, resolve the model and the
    workspace (recording `last_error` and starting nothing when either is unusable), otherwise build the
    `RunRequest` with `mode=effective_mode(...)` and call `start`, then advance `next_run_at` from `now`.
  - `run_now(schedule_id)` and `skip_missed(schedule_id)`.
  - `start()`/`stop()` for the lifespan; interval a module constant.
- `backend/server/app.py`: create the scheduler in the lifespan, hand it `lambda request: (await runs()).start(request)`,
  cancel it on shutdown. Nothing starts at import time.
- `backend/tests/test_schedule_ticker.py`: an overdue schedule becomes `missed` and starts nothing; `run_now` starts
  exactly one run with the effective mode and clears `missed`; `skip` clears it and starts nothing; a disabled
  schedule never starts; an expired one never starts; a missing model records `last_error` and starts nothing; two
  due schedules both start (D40); a slow run does not delay the other.
- `backend/tests/test_schedule_run.py`: a scheduled run with `mode=ask` whose prompt makes the demo model write
  produces a pending approval, a `run.finished` that has not arrived, and one queued approval attributed to that
  schedule; the same schedule in `auto` still escalates a high-risk command (R8); answering the approval lets the
  run finish. This is the "queued approval pauses the run" test from the brief.

Commit: `feat(schedule): a ticker that offers missed runs and starts real ones`

## Step 4: The routes
- `backend/server/schedules.py`: `schedules_routes(catalog, scheduler)` with `GET /schedules`, `POST /schedules`,
  `PUT /schedules/{id}`, `DELETE /schedules/{id}`, `POST /schedules/{id}/run`, `POST /schedules/{id}/skip`.
  Validation errors are 422 through the existing handler; an unknown id is 404; a schedule whose workspace is gone is
  refused at creation (400) rather than stored and failed later.
- `ScheduleRecord`, `ScheduleList` and `ScheduleInput` join the `Protocol` envelope; run `npm run generate:protocol`
  and commit the generated `src/lib/protocol.ts`.
- `backend/tests/test_schedule_routes.py`: the full create → list → update → delete round trip, the 404s, the
  refusal of a bad workspace, and `next_run_at` present on every created record.

Commit: `feat(schedule): the schedule routes and generated wire types`

## Step 5: Copy, pure helpers, and the hook
- `src/i18n/schedule.ts`: `scheduleCopy(locale)` — `en` first, `fa` typed against it — with the mock's strings
  (title, subtitle, `active` count label, `paused`, `new`, template titles and prompts, row statuses, dialog labels,
  the full-access warning, errors, delete confirmation) and `templates` as a typed list.
- `src/lib/schedule.ts`: `effectiveMode(mode, ceiling)`, `recurrenceLabel(schedule, copy)`,
  `nextRunLabel(schedule, now, locale, copy)`, `relativeDay(at, now, locale)`, `lastResultLabel`, `formatTime`.
  No React, no fetch.
- `src/lib/use-schedules.ts`: fetch, create, update, delete, run now, skip, toggle; one `busy` and one `error`.
- `tests/unit/schedule.test.ts`: the six-cell matrix (D42), every recurrence label, the status label per
  `last_status`, Persian digits in Persian output, relative-day edges (today, yesterday, older), and a scan that
  every template in the copy list has a prompt and a name in both locales.

Commit: `feat(schedule): the copy module, the display helpers and the hook`

## Step 6: The screen
- `src/components/schedule/schedule-screen.tsx`, `schedule-row.tsx`, `templates.tsx`.
- `src/app/schedule/page.tsx` → `<TaskScreen initialView="schedule" />`; `"schedule"` joins the view union and the
  render branch in `task-screen.tsx`; the sidebar item becomes `<a href="/schedule/">` and marks itself active.
- `src/lib/states.ts`: `WIRED.noSchedules = "schedule"`; `src/i18n/states.ts`: the help text stops claiming there is
  no scheduler and the primary action becomes "add a schedule"; `tests/unit/states.test.ts`: the allowance becomes a
  requirement that the state is reachable and *does* offer the add action.
- `src/app/globals.css`: row, switch, chip and template-grid rules from tokens only, logical properties only.
- `tests/unit/schedule.test.ts` gains the state wiring assertion; `tests/unit/theme.test.ts` and
  `tests/unit/logical-css.test.ts` pass unchanged on the new CSS.

Commit: `feat(schedule): the schedule screen, its rows, the templates, and the empty state it fills`

## Step 7: The dialog
- `src/components/schedule/schedule-dialog.tsx`: create and edit in one component. Name, prompt with the
  improve-text button and the mode chip, workspace select, ceiling chip, the red warning when full access is chosen,
  repeat, weekday when weekly, time, validity, Cancel, Confirm. Confirm disabled on an empty name or prompt or no
  workspace; the dialog stays open on an error and shows it.
- `src/components/schedule/delete-schedule.tsx`: one confirmation naming what is lost (D32's shape: name the loss).
- Escape closes through `src/lib/shortcuts.ts`'s `dialog` scope; focus lands on the name field.

Commit: `feat(schedule): the add and edit dialog, with the stricter of two permissions`

## Step 8: Walkthrough, record, roadmap
- `tests/phase9b-desktop.ts`: launch once, open the empty state, create a schedule through the dialog, assert the
  row, the Persian digits and the next-run text; restart on the same profile and assert the schedule is still there
  with a recomputed next occurrence; switch it off and assert the paused group; delete it and assert the empty state
  returns; a second launch with an overdue schedule asserts the missed-run prompt offers "run now" and that nothing
  started by itself. Evidence into `artifacts/phase9b-*.png`.
- Run every gate; tick `validation.md` with the test that proves each box; write `learnings.md`; mark row 9b in
  `roadmap.md` complete, add the decisions D34–D42 and the handoff to Phase 10; correct the Phase 9 handoff line
  that claimed the empty state needed no new copy.

Commit: `test(phase9b): the schedule walkthrough, the record, and the roadmap`

## Ordering rules
- Step 3 needs Step 2; Step 4 needs Step 3; Steps 5–7 need Step 4's generated types; Step 8 needs all of them.
- The engine steps (1–4) are independently shippable: after Step 4 the feature works from the API and the UI is the
  only thing missing.
- Step 6 needs the answers to Q1 and Q2 in `requirements.md`; Steps 1–5 do not.
