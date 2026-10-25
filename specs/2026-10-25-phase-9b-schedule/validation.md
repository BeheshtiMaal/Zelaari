# Phase 9b: Schedule. Validation

Done only when every box is ticked with the test or the evidence that proves it. Boxes are unchecked until the step
that proves them exists.

## Automated (CI)

### Recurrence and permission table (Step 1)
- [ ] R1 daily at 02:00 asked at 01:00 returns today 02:00; asked at 02:00:00 returns tomorrow 02:00;
      `test_schedule_math.py::test_daily_boundary_is_strictly_after`.
- [ ] R1 weekly Friday 09:00 asked on Wednesday returns that Friday; asked on Friday at 09:00:00 returns the next
      Friday; `::test_weekly_friday_0900`.
- [ ] R1 a weekly schedule with a missing or out-of-range weekday is refused at validation, not at run time;
      `::test_weekly_requires_a_weekday`.
- [ ] R2 a run at 09:00 on the until date still happens; the next occurrence after it is `None`; `::test_validity_is_inclusive_then_expires`.
- [ ] R6 all six cells of the mode × ceiling table; `::test_effective_mode_matrix`.
- [ ] R6 `report` never yields ask or auto, and `full` never upgrades a read-only mode; `::test_ceiling_only_ever_tightens`.
- [ ] A clock jump over a scheduled time starts that run once, late, and never twice;
      `::test_clock_jump_starts_one_late_run`.

### Persistence (Step 2)
- [ ] R3 a created schedule reloads from the same `catalog.json` with identical fields and a recomputed
      `next_run_at`; `test_schedule_store.py::test_survives_restart`.
- [ ] R3 nothing about a schedule appears under the workspace's `.harness/`;
      `::test_schedule_never_written_to_the_workspace`.
- [ ] R3 a catalog written before this phase (no `schedules` key) loads with an empty list;
      `::test_old_catalog_loads_with_no_schedules`.

### Ticker and missed runs (Step 3)
- [ ] R10 an overdue schedule at startup becomes `missed` with the time it was due, and starts nothing;
      `test_schedule_ticker.py::test_overdue_becomes_missed_and_starts_nothing`.
- [ ] R10 "run now" starts exactly one run, with the effective mode, and clears `missed`;
      `::test_run_now_starts_one_run_and_clears_missed`.
- [ ] R10 "skip" clears `missed` and starts nothing; `::test_skip_starts_nothing`.
- [ ] R10 `next_run_at` advances from *now* after a start, so a slow run or a long sleep never produces a burst;
      `::test_next_run_advances_from_now`.
- [ ] R11 a disabled schedule never starts; `::test_disabled_never_starts`.
- [ ] R2 an expired schedule never starts and is reported as expired; `::test_expired_never_starts`.
- [ ] R12 a missing or unusable model records `last_error` and starts nothing; `::test_missing_model_is_reported`.
- [ ] R12 a workspace that moved is reported and starts nothing; `::test_moved_workspace_is_reported`.
- [ ] R4 and D40: two schedules due in the same tick both start, and a run still executing does not delay the second;
      `::test_two_due_schedules_both_start`.
- [ ] R9 a scheduled run in ask mode that writes raises an approval, has not finished, and is attributed to its
      schedule; answering it lets the run finish;
      `test_schedule_run.py::test_queued_approval_pauses_and_resumes_the_run`.
- [ ] R8 the same schedule in auto still escalates a high-risk command to an approval;
      `::test_full_access_never_bypasses_the_always_ask_list`.
- [ ] R5 the scheduled run writes its own `events.jsonl` under its workspace and a `TaskRecord` with `schedule_id`;
      `::test_scheduled_run_is_an_ordinary_run`.

### Routes and wire types (Step 4)
- [ ] create → list → update → delete round trip; `test_schedule_routes.py::test_round_trip`.
- [ ] an unknown id is 404 and an invalid body is 422 without echoing the input; `::test_not_found_and_invalid`.
- [ ] creating a schedule for a workspace that does not exist is refused; `::test_bad_workspace_is_refused`.
- [ ] `src/lib/protocol.ts` is generated from the `Protocol` envelope and a second run leaves the tree clean;
      `npm run generate:protocol` twice, `git status` empty.

### UI contracts (Steps 5–7)
- [ ] R6 the dialog's `effectiveMode` agrees with the engine on all six cells; `tests/unit/schedule.test.ts`.
- [ ] R19 every schedule string exists in fa and en with the same shape, the same placeholders, Persian digits in
      Persian and no Persian literal in a component; `tests/unit/i18n.test.ts` (discovers the new module) and
      `tests/unit/schedule.test.ts`.
- [ ] R13/R14 every template has a name and a prompt in both locales; `tests/unit/schedule.test.ts`.
- [ ] R16 the empty state is reachable and offers the add action, and `WIRED.noSchedules` is `"schedule"`;
      `tests/unit/states.test.ts`.
- [ ] R20 the new CSS uses tokens only and logical properties only; `tests/unit/theme.test.ts`,
      `tests/unit/logical-css.test.ts`.
- [ ] Every gate: `ruff`, `mypy --strict backend`, `pytest`, `npx tsc --noEmit`, `npm run test:ui`,
      `npm run build`, `npm run build:electron`, `npm run test:desktop`.

## Manual (Windows 10/11)
- [ ] R13 the screen matches `Schedule.dc.html`: header, subtitle, group label with the count, row anatomy, template
      grid, spacing and radii. Screenshot compared side by side.
- [ ] R14 the dialog matches `ScheduleAdd.dc.html`: the prompt box with the mode chip inside it, the ceiling chip
      under it, the red warning, the three fields in one row, Cancel/Confirm at the end.
- [ ] R7 the dialog opens on read-only + report, and choosing full access shows the red warning immediately.
- [ ] R19 the whole screen reads correctly in Persian (RTL, Persian digits) and in English (LTR, Latin digits) with
      no clipped row and no mirrored control.
- [ ] R10 with a schedule made overdue by moving the clock forward, the next launch shows the missed prompt with
      "run now" and "skip", and no run has started by itself.
- [ ] R18 delete asks once, names the schedule, and the runs it already produced remain under the workspace.
- [ ] R17 the sidebar's Schedule item navigates, marks itself active, and no longer carries the "later phase"
      tooltip.
- [ ] Keyboard only: Tab reaches the switch, Space toggles it, Escape closes the dialog, focus returns to the
      button that opened it.

## Exit criteria
Every box ticked with evidence, all gates green, `learnings.md` written (what was verified, deviations, surprises,
open items), `roadmap.md` row 9b complete with the decisions and the Phase 10 handoff.
