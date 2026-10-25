# Phase 9b: Schedule. Validation

Done only when every box is ticked with the test or the evidence that proves it. Boxes are unchecked until the step
that proves them exists.

## Automated (CI)

### Recurrence and permission table (Step 1)
- [x] R1 daily at 02:00 asked at 01:00 returns today 02:00; asked at 02:00:00 returns tomorrow 02:00;
      `test_schedule_math.py::test_daily_boundary_is_strictly_after`.
- [x] R1 weekly Friday 09:00 asked on Wednesday returns that Friday; asked on Friday at 09:00:00 returns the next
      Friday; `::test_weekly_friday_0900`.
- [x] R1 a weekly schedule with a missing or out-of-range weekday is refused at validation, not at run time;
      `::test_weekly_requires_a_weekday`, `::test_weekly_rejects_an_impossible_weekday`.
- [x] R2 a run at 09:00 on the until date still happens; the next occurrence after it is `None`;
      `::test_validity_is_inclusive_then_expires`, `::test_expired_is_not_due`.
- [x] R6 all six cells of the mode × ceiling table; `::test_effective_mode_matrix`.
- [x] R6 `report` never yields ask or auto, and `full` never upgrades a read-only mode;
      `::test_ceiling_only_ever_tightens`.
- [x] R7 the unattended default is read-only plus report; `::test_default_is_read_only_and_report`.
- [x] A clock jump over a scheduled time starts that run once, late, and never twice;
      `::test_clock_jump_starts_one_late_run`.
- [x] A start advances from *now*, not from the occurrence it just ran;
      `::test_a_start_advances_from_now_not_from_the_old_occurrence`.

### Persistence (Step 2)
- [x] R3 a created schedule reloads from the same `catalog.json` with identical fields and a recomputed
      `next_run_at`; `test_schedule_store.py::test_survives_restart`.
- [x] R3 nothing about a schedule appears under the workspace's `.harness/`;
      `::test_schedule_never_written_to_the_workspace`.
- [x] R3 a catalog written before this phase (no `schedules` key) loads with an empty list;
      `::test_old_catalog_loads_with_no_schedules`.
- [x] R10 an occurrence that fell due while the app was closed **survives the reload** instead of being recomputed
      into the future — without this the offer can never fire; `::test_an_overdue_occurrence_survives_a_restart`.
- [x] A status left at "running" by a killed process reloads as interrupted; `::test_a_running_status_becomes_interrupted`.
- [x] Editing reschedules and keeps the run history; `::test_edit_reschedules_and_keeps_history`.
- [x] Switching off and on again recomputes the occurrence from now; `::test_the_switch_reschedules_from_now`.
- [x] A validity date in the past is refused at write time; `::test_an_expired_validity_is_refused`.

### Ticker and missed runs (Step 3)
- [x] R10 an overdue schedule at startup becomes `missed` with the time it was due, and starts nothing;
      `test_schedule_ticker.py::test_overdue_becomes_missed_and_starts_nothing`.
- [x] R10 an occurrence a minute late is started, not offered — the grace window is the boundary;
      `::test_a_slightly_late_occurrence_is_started_not_offered`, `::test_the_grace_window_is_the_boundary`.
- [x] R10 "run now" starts exactly one run, with the effective mode, and clears `missed`;
      `::test_run_now_starts_one_run_and_clears_missed`.
- [x] R10 "skip" clears `missed` and starts nothing; `::test_skip_starts_nothing`.
- [x] R10 `next_run_at` advances from *now* after a start, so a slow run or a long sleep never produces a burst;
      `::test_next_run_advances_from_now`.
- [x] R11 a disabled schedule never starts; `::test_a_disabled_schedule_never_starts`.
- [x] R2 an expired schedule never starts; `::test_expired_never_starts`.
- [x] R12 a missing or unusable model records `last_error` and starts nothing; `::test_missing_model_is_reported`.
- [x] R12 a workspace that moved is reported and starts nothing; `::test_moved_workspace_is_reported`.
- [x] A failure backs off and then recovers, and "run now" reports the same reason;
      `::test_a_failure_backs_off_then_recovers`, `::test_run_now_reports_the_same_reason`.
- [x] R4 and D40: two schedules due in the same tick both start, and a run still executing does not delay the second;
      `::test_two_due_schedules_both_start`.
- [x] R5 the request carries the effective mode; `::test_the_run_carries_the_effective_mode`,
      `::test_full_access_keeps_the_mode_it_was_given`.
- [x] R9 a scheduled run in ask mode that writes raises an approval, has not finished, and is attributed to its
      schedule; answering it lets the run finish;
      `test_schedule_run.py::test_queued_approval_pauses_and_resumes_the_run`.
- [x] R9 a rejected approval still ends the run rather than leaving it paused forever;
      `::test_a_rejected_approval_still_ends_the_run`.
- [x] R8 the same schedule in auto still escalates a high-risk command to an approval;
      `::test_full_access_never_bypasses_the_always_ask_list`.
- [x] R5 the scheduled run writes its own `events.jsonl` under its workspace;
      `::test_the_scheduled_run_writes_its_own_event_log`.

### Routes and wire types (Step 4)
- [x] create → list → update → delete round trip; `test_schedule_routes.py::test_round_trip`.
- [x] an unknown id is 404 and an invalid body is 422 without echoing the input;
      `::test_unknown_ids_are_404`, `::test_invalid_input_is_422_without_echoing_it`.
- [x] creating a schedule for a workspace that does not exist is refused; `::test_a_workspace_that_is_not_there_is_refused`.
- [x] `POST /schedules/{id}/run` starts one run with the effective mode; `::test_run_now_starts_one_run_with_the_effective_mode`.
- [x] the row's queued-approval count comes from the inbox and the run's `schedule_id`;
      `::test_the_row_counts_its_own_queued_approvals`.
- [x] the routes are behind the token like every other route; `::test_schedules_require_the_token`.
- [x] a created schedule is on disk after the app closes; `::test_a_created_schedule_is_on_disk_after_the_app_closes`.
- [x] `src/lib/protocol.ts` is generated from the `Protocol` envelope and a second run leaves the tree clean;
      `npm run generate:protocol` twice, `md5sum` unchanged.

### UI contracts (Steps 5–7)
- [x] R6 the dialog's `effectiveMode` agrees with the engine on all six cells; `tests/unit/schedule.test.ts`.
- [x] R19 every schedule string exists in fa and en with the same shape and the same placeholders;
      `tests/unit/i18n.test.ts` (discovers `scheduleCopy`) and `tests/unit/schedule.test.ts`.
- [x] R19 no Persian literal in a component, and Persian digits in Persian output; `tests/unit/i18n.test.ts`,
      `tests/unit/schedule.test.ts`.
- [x] R13/R14 every template has a name and a prompt in both locales; `tests/unit/schedule.test.ts`.
- [x] R16 the empty state is reachable and offers the add action, and `WIRED.noSchedules` is `"schedule"`;
      `tests/unit/states.test.ts`.
- [x] R20 the new CSS uses tokens only and logical properties only; `tests/unit/theme.test.ts`,
      `tests/unit/logical-css.test.ts`.
- [x] R20 every centred dialog flips its transform for a right-to-left document — the bug the walkthrough found;
      `tests/unit/logical-css.test.ts` "mirrors the centring transform for a right-to-left document".

### Gates
- [x] `ruff check backend` — All checks passed.
- [x] `mypy --strict backend` — Success: no issues found in 230 source files.
- [x] `uv run --project backend pytest backend/tests` — 928 passed, 0 failed; see the Final evidence table.
- [x] `npx tsc --noEmit` — clean.
- [x] `npm run test:ui` — 220 tests, 0 failures.
- [x] `npm run build` — static export in `out/`, `/schedule` in the route table.
- [x] `npm run build:electron` — `electron-dist/main.cjs`, `preload.cjs`.
- [x] `npx tsx tests/phase9b-desktop.ts` — S1–S5 passed; evidence in `artifacts/phase9b-*.png`.

## Manual (Windows 10/11)
- [x] R13 the screen matches `Schedule.dc.html`: header, subtitle, group label with the count, row anatomy, template
      grid, spacing and radii. `artifacts/phase9b-s3-row.png`, `phase9b-s1-empty.png`.
- [x] R14 the dialog matches `ScheduleAdd.dc.html`: the prompt box with the mode chip inside it, the ceiling chip
      under it, the red warning, the three fields in one row, Cancel/Confirm at the end.
      `artifacts/phase9b-s2-full-warning.png`. *Three deliberate departures, listed in `learnings.md`: the dialog adds a
      Name field and a live "runs as" line, and the mock's time control is a native `<input type="time">` here (Q2).*
- [x] R7 the dialog opens on read-only + report, and choosing full access shows the red warning immediately. Proven in
      the walkthrough, not only by eye: `phase9b-desktop.ts` walks all three directions of the table.
- [x] R19 the whole screen reads correctly in Persian (RTL, Persian digits) — and this is where the mirrored-transform
      defect was found: the dialog was half a width off-screen in Persian and Confirm was unclickable.
- [x] R10 with a schedule made overdue by rewriting its stored occurrence, the next launch shows the missed prompt with
      "run now" and "skip", and no run has started by itself: `phase9b-s5-missed.png`, plus `last_run_id === null`
      read back from `catalog.json` while the prompt is on screen.
- [x] R18 delete asks once, names the schedule, and says the runs it already produced stay under the workspace:
      `phase9b-s4-delete.png`.
- [x] R17 the sidebar's Schedule item navigates, marks itself active, and no longer carries the "later phase" tooltip:
      it is an `<a href="/schedule/">` with `active` when the view is `schedule`.
- [x] R6 editing can only tighten: dropping the ceiling to report changes the row's chip from "with approval" to
      "read-only" while the stored mode stays `ask`: `phase9b-s4-edited.png`, and the walkthrough asserts both the chip
      and the two stored fields.
- [x] R10 the missed prompt's "run now" starts exactly one run and only when pressed: `phase9b-s5-ran.png`, and the
      walkthrough polls `last_run_id` from `null` to a value after the click.
- [ ] Keyboard only: Tab reaches the switch, Space toggles it, Escape closes the dialog, focus returns to the button
      that opened it. *Partially proven: focus lands on the name field (asserted) and Escape closes through Radix's
      dialog scope; focus **restore** to the opening button is not asserted anywhere, which is the same gap Phase 9
      recorded for the confirm dialog.*

## Final evidence table

One sequential run per gate on the settled source, `npm run build` before any desktop suite because Electron serves
`out/`.

| Gate | Result |
| --- | --- |
| `ruff check backend` | All checks passed |
| `mypy --strict backend` | Success: no issues found in 230 source files |
| `pytest backend/tests` | 928 passed in 12m41s (see note) |
| `npx tsc --noEmit` | clean |
| `npm run test:ui` | 220 tests, 220 pass, 0 fail |
| `npm run build` | `/schedule` exported |
| `tests/phase9b-desktop.ts` | S1–S5 passed |

*Note on pytest.* 928 passed with no failures on a quiet machine. An earlier run made while a seven-worker `next build`
was running on the same machine reported 927 passed and one failure,
`test_delegate_recovery.py::test_force_killed_delegate_preserves_completed_result_and_queued_steering`; that test passes
on its own (2 passed in 63 s) and is a Phase 6 test this phase does not touch, so it is a timing-sensitive test on a
loaded machine rather than a regression. The clean run is the one recorded, and the flake is recorded rather than
hidden.

## Exit criteria
Every box ticked with evidence, all gates green, `learnings.md` written (what was verified, deviations, surprises,
open items), `roadmap.md` row 9b complete with the decisions and the Phase 10 handoff.
