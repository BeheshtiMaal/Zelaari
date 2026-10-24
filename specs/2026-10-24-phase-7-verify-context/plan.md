# Phase 7: Verify, self-correction, context ring. Plan

Work top to bottom. One commit per step, conventional message, no bundling. A step is done when its tests pass and
`validation.md` items it covers are checked.

## Step 0: spec
`requirements.md`, `plan.md`, `validation.md`; propose the five decisions for the roadmap log. No product code. Stop for
approval.

## Step 1: settings and detection (R1, R2)
- `backend/verify/__init__.py`, `backend/verify/detection.py` (pure `detect`, bounded walk, no execution),
  `backend/verify/settings.py` (`ContextSettings`, `VerifySettings`, `TerminalSettings`, `VerifyConfig`, `load`/`save` in
  `.harness/config.json`, defaults from the mock, unknown keys rejected).
- `backend/server/verify.py`: `GET /verify/settings?workspace=` (config + live detection),
  `PUT /verify/settings?workspace=` (validate → protected-configuration approval → atomic write).
- Register the router in `server/app.py`; add the models to the protocol envelope in `agent/events.py`.
- Tests: `backend/tests/test_test_detection.py` (the matrix: custom, pytest.ini, pyproject, tests/, npm, placeholder script,
  both runners, none, jail/symlink safety, bounded walk), `backend/tests/test_verify_settings.py` (defaults, validation,
  approval path, corrupt config, atomicity).

## Step 2: test results and the `test.result` event (R7)
- `backend/verify/results.py`: `parse_test_output(command, exit_code, timed_out, text) -> TestResult` for pytest and
  npm-style output; bounded failures and summary.
- `agent/events.py`: real `TestResult` event, remove `test.result` from `FutureEvent`.
- Bridge: when a `run_command` result is the verification command, emit `test.result` next to the existing `tool.result`.
- Tests: `backend/tests/test_test_results.py` (pytest summaries, mocha/jest summaries, unknown counts, timeouts, truncated
  output, redaction of a canary secret in the excerpt).

## Step 3: verify gate (R3, R6)
- `backend/verify/gate.py`: `VerifyState` (mutations, verifications, injections, command) and `VerifyGateMiddleware`
  (`awrap_tool_call` records results; `aafter_model` decides with `@hook_config(can_jump_to=["model"])` and injects the
  `[harness]` message). Emits `verify.required`.
- Unknown command path: one instruction to call `ask_user_question`, adopt the answered command, decline turns the gate off.
- `agent/factory.py`: accept and place the middleware after the permission gate; `agent/bridge.py`: resolve the command at
  run start (setting → detection) and pass it in.
- Scripted offline fixtures in `providers/verify_demo.py` (dispatched from `providers/demo.py` by task prefix, the Phase 6
  pattern): `demo verify gate`, `demo verify fail`, `demo verify budget`, `demo verify question`, `demo verify context`.
  They are test infrastructure for both `pytest` and the Electron walkthrough, so the UI scenarios stay deterministic and
  offline.
- Tests: `backend/tests/test_verify_gate.py` — gate blocks a finish after a successful edit, allows it after `exit_code 0`,
  ignores a failed verification, ignores a denied/failed mutation, respects `gate: false` and read-only mode, caps at 3
  injections, and the question path (scripted model that calls `ask_user_question`) plus decline.

## Step 4: budgets and the reflect loop (R4, R5)
- `backend/verify/budget.py`: `Budget` counters and `BudgetMiddleware` (step on each model turn with tool calls, wall clock
  from run start, fix attempts per plan step, `budget.updated`, `budget.exhausted`, cancellation through the existing stop
  path).
- Exhaustion: build the Phase 5 exhausted card through `exhausted_question`; wire `retry` / `change` / `stop` / declined to
  the gate and the budget (hint injection, plan-revision requirement, gate suspension).
- `agent/bridge.py`: read the settings, pass them in, map the exhaustion outcome onto the existing question barrier.
- Tests: `backend/tests/test_budget.py` (step cap, wall-clock cap with a fake clock, fix-attempt counter per step, retry
  resets and injects the hint, change requires a revision, stop suspends the gate, declined behaves as stop).

## Step 5: compaction and summary handoff (R13, R14)
- `agent/summarization.py`: accept `trigger` / `keep` / offload from settings; persist the redacted summary to
  `.harness/context/summaries/<run_id>.md`.
- `agent/bridge.py`: `GET /runs/{id}/summary`; `seed_summary_from` prepends the bounded summary block.
- Tests: `backend/tests/test_compaction.py` (trigger fraction and keep from settings, `context.summarized` once per
  operation, summary file redacted and bounded, missing summary → 404, seeded run carries the block, oversized summary is
  truncated).

## Step 6: context breakdown (R12)
- `backend/verify/context.py`: `breakdown(messages, system, tools)` with `count_tokens_approximately`.
- `agent/projection.py`: attach `breakdown` to `context.updated`.
- Tests: `backend/tests/test_context_breakdown.py` (categories sum, tool messages counted separately, system + tools counted,
  skills/memory zero, estimates flagged).

## Step 7: context ring and popover (R10, R11)
- `src/lib/context-format.ts`: `formatTokens` (`۴۸٫۸K`), `formatPercent`, `tooltipText`, `arcDash`, `thresholdAngle`,
  `breakdownRows` — pure and unit tested.
- `src/components/context/context-ring.tsx` (arc + Radix tooltip) and `context-breakdown.tsx` (popover, bars, marker,
  `new chat with summary`), wired into `src/components/composer.tsx`.
- `src/i18n/context.ts` (fa/en), replace `placeholderRing`.
- Tests: `tests/unit/context.test.ts` (tooltip at 38 %/48.8K/128K, estimated `~`, zero and clamped values, arc length,
  marker position at 60 %, row proportions).

## Step 8: terminal and test results (R8, R9)
- Add `@xterm/xterm` and `@xterm/addon-fit`; `src/components/run/terminal-panel.tsx` (read-only, fit addon, resize
  observer, header, exit code, timeout variant) and `src/components/run/test-results.tsx`.
- `src/lib/test-results.ts`: read `test.result` events for a call, fall back to the `run_command` payload.
- Mount both in `src/components/planning/activity-timeline.tsx` where a command call is rendered; `src/app/globals.css`
  tokens (`--terminal`, header, chips).
- Tests: `tests/unit/terminal.test.ts` (payload parsing, timeout flag, line cap, unknown counts fall back to the exit code).

## Step 9: settings screens (R15)
- `src/components/settings/context-settings.tsx`, `terminal-settings.tsx`, `src/lib/use-verify-settings.ts` (mirrors the
  planning-settings hook, including the inline approval card).
- `src/i18n/verify.ts` (fa/en) with the mock's exact strings; render in `settings-screen.tsx` sections 3 and 4 instead of the
  deferred panel.
- Tests: `tests/unit/verify-settings.test.ts` (form ↔ model mapping, bounds, detection labels, shell options, locked row).

## Step 10: run panel and meter (R16)
- `src/components/planning/run-info.tsx`: real context occupancy and budget counters from `budget.updated`; remove the
  "unavailable" placeholders for these two rows only.
- Run header: cumulative tokens with `~` when estimated.
- Tests: `tests/unit/run-info.test.ts` (counter rendering, estimate marker, missing events).

## Step 11: Electron walkthrough suite (`tests/phase7-desktop.ts`)
- Playwright-driven Electron like `tests/phase6-desktop.ts`: disposable workspace and profile, offline scripted models,
  `artifacts/phase7/` screenshots and `evidence.json`. A pytest fixture project whose `test_parser.py` fails then passes,
  and a hanging command fixture for the timeout variant.
- Implement scenarios S1–S10 from `validation.md` as real assertions on DOM state, persisted `events.jsonl`, `tool.call`
  args, `request.json`, the summary file and the process tree — no screenshot-only checks, no manual steps.
- Wire it into the same script family as the other phase suites (`npx tsx tests/phase7-desktop.ts`) and run the existing
  baseline suites (S10) against the final build.

## Step 12: validate and record
- Run every gate in the "Final evidence" table sequentially on settled source; run `tests/phase7-desktop.ts` and the
  baseline desktop suites; tick `validation.md` with evidence (test names, artifact paths, event ids); write `learnings.md`
  (verified APIs, fixture design, deviations, any TODO); update `roadmap.md` (phase row, decisions log, handoff to Phase 8).
