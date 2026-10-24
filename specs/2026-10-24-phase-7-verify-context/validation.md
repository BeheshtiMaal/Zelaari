# Phase 7: Verify, self-correction, context ring. Validation

Every box below is automated: engine tests, UI unit tests, or a Playwright-driven Electron walkthrough against a disposable
workspace and profile with scripted offline models. Nothing depends on a human eyeballing a window.

Status: **complete.** Final gates ran sequentially on settled source at Step 12; the "Final evidence" table records that run.

## Final evidence

One sequential run per gate on settled source (no concurrent typecheck/build).

| Gate | Result |
| --- | --- |
| `uv run --project backend ruff check backend` | All checks passed |
| `uv run --project backend mypy --strict backend` | Success: no issues found in 144 source files |
| `uv run --project backend pytest backend/tests` | **531 passed**, 2 warnings in 660.79 s (`artifacts/phase7/pytest.log`) |
| `npm run typecheck` | clean (no output) |
| `npm run test:ui` | **68 passed**, 0 failed |
| `npm run generate:protocol` + `npm run generate:genui` | both ran, `git status src/lib/` empty (no diff) |
| `npm run build` | passed, 6 static routes |
| `npm run build:electron` | `main.cjs` 750.5 kb, `preload.cjs` 708 b |
| `npm run test:desktop` | "Persian/English, real demo read + OpenUI, replay, auth, loopback, normal and forced cleanup passed" |
| `tests/phase7-desktop.ts` | all S1–S9 passed, 14 evidence lines, `artifacts/phase7/evidence.json` |

Named Phase 7 engine suites: `test_test_detection` (14), `test_verify_settings` (9), `test_test_results` (13),
`test_verify_gate` (16), `test_budget` (18), `test_compaction` (9), `test_context_breakdown` (6) — 85 cases, plus the
existing permission/approval/question/recovery regressions.

Named Phase 7 UI suites: `tests/unit/context.test.ts` (6), `tests/unit/terminal.test.ts` (4),
`tests/unit/verify-settings.test.ts` (8), `tests/unit/run-info.test.ts` (4) — 22 cases, plus the interrupted-card
classification added to `tests/unit/errors.test.ts`.

Artifacts: `artifacts/phase7/evidence.json`, `artifacts/phase7/pytest.log`, `artifacts/phase7/walkthrough.log`,
`artifacts/phase7/desktop-baseline.log`, `artifacts/phase7/phase4-baseline3.log`, `artifacts/phase7/phase5-baseline-1.log`,
`artifacts/phase7/phase5-baseline-2.log`, `artifacts/phase7/phase6-baseline.log` and the screenshots named per scenario
below.

## Automated: engine and units

- [x] **Gates.** `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`, `npm run test:ui` green. — see the table above.
- [x] **R1** Detection matrix: custom command wins; `pytest.ini`; `pyproject.toml` mentioning pytest; `tests/` with  
  `test_*.py`; `package.json` `scripts.test`; npm's placeholder script is ignored; both runners present → pytest;  
  nothing → `none`. `test_test_detection.py` — 14 cases, including `custom command wins over every marker` and
  `both runners present picks pytest`.
- [x] **R1** Detection never leaves the workspace: a symlink/junction inside `tests/` pointing outside is not followed, and  
  `.harness/`, `.git/`, `node_modules/` are skipped; the walk is bounded. `test_test_detection.py` — the link case asserts
  the outside file is not counted; the skipped directories and the 10 000-entry bound are separate cases.
- [x] **R2** Settings load/save round-trips the three sections; every out-of-range value is rejected without writing; a  
  corrupt or missing config yields the documented defaults; the write is atomic and needs the configuration approval.  
  `test_verify_settings.py` — 9 cases; the rejection case asserts the file bytes are unchanged.
- [x] **R2** `GET /verify/settings` reports the live detection for the selected workspace. `test_verify_settings.py` —
  `test_settings_report_live_detection` reads a real `pyproject.toml` in the workspace.
- [x] **R3** The gate blocks a finish after a successful `edit_file` and allows it after a verification command returns  
  `exit_code 0`; a failed verification does not satisfy the gate. `test_verify_gate.py` — 16 cases across the gate suite.
- [x] **R3** The gate ignores denied or failed mutations, `gate: false`, and read-only mode. `test_verify_gate.py` — one
  case per condition; read-only runs never reach a mutation.
- [x] **R3** The gate stops blocking after 3 consecutive injections and emits `budget.exhausted {kind: "verify"}`.  
  `test_verify_gate.py` — `test_gate_gives_up_after_three_injections`.
- [x] **R6** With no resolvable command the gate asks through `ask_user_question` and adopts the answered command; a declined  
  card turns the gate off and emits `verify.required {blocked: false}`. `test_verify_gate.py` — the question and decline
  cases; the walkthrough S2 decline path asserts the same silence through the real barrier.
- [x] **R4** The step counter, wall clock and per-step fix attempts are real and published in `budget.updated`;  
  `max_steps` and `max_minutes` stop the run with `budget.exhausted` then `run.finished {stopped}`. `test_budget.py` — 18
  cases; walkthrough S3 proves both caps through the real engine.
- [x] **R5** At `fix_attempts` the exhausted card is raised on the normal barrier; `retry` injects the hint and resets the  
  counter, `change` requires a plan revision, `stop` reports once and finishes `completed`, `declined` behaves as `stop`.  
  `test_budget.py` — one case per choice; walkthrough S2 runs all four through the real QuestionCard.
- [x] **R7** `test.result` parsing: pytest summary, mocha/jest summary, unknown counts, timeout, truncated output, canary  
  secret never appears in the excerpt. `test_test_results.py` — 13 cases including the canary excerpt.
- [x] **R13** The summarizer receives the configured fraction and keep count; `context.summarized` is emitted once per  
  operation; the persisted summary is redacted and bounded. `test_compaction.py` — 9 cases; the walkthrough asserts one
  notice per distinct `operation_id` (S6).
- [x] **R14** `/runs/{id}/summary` returns the summary, 404 without one, and a seeded run carries the bounded block.  
  `test_compaction.py`; walkthrough S6 reads the new run's `request.json` (`seed_summary_from` + the block).
- [x] **R12** The breakdown sums to the counted total, tool results are separate from messages, system + tools are counted,  
  skills and memory are 0, and the estimate flag is set. `test_context_breakdown.py` — 6 cases.
- [x] **R10** Tooltip text at 38 % / 48.8K / 128K equals the mock's string with Persian digits; estimated values get `~`;  
  0 % and over-100 % are clamped. `tests/unit/context.test.ts` — 6 cases.
- [x] **R11** Arc length and threshold marker position match the configured percentage; row bars are proportional.  
  `tests/unit/context.test.ts`; walkthrough S5 compares the live `stroke-dashoffset` with `arcDash` of the event value.
- [x] **R8** Terminal payload parsing: exit code, timeout flag, line cap, unknown counts fall back to the exit code.  
  `tests/unit/terminal.test.ts` — 4 cases.
- [x] **R15** Settings forms map to the model, enforce the bounds, show the detection label and the shell options, and keep  
  the locked row read-only. `tests/unit/verify-settings.test.ts` — 8 cases; S7/S8 assert the rendered rows against the mock.
- [x] **R16** The run panel renders real counters and the `~` estimate marker; missing events render as unavailable, not as  
  zero. `tests/unit/run-info.test.ts` — 4 cases.
- [x] **Wire** `src/lib/protocol.ts` is regenerated (not hand-edited) and includes `test.result`, `budget.updated`,  
  `budget.exhausted`, `verify.required`, `context.updated.breakdown` and `RunRequest.seed_summary_from`. — regeneration
  produced no diff; `seed_summary_from` (line 1011) and `breakdown` (line 913) are in the generated file.

## Automated Windows Electron walkthroughs (`tests/phase7-desktop.ts`)

Real Electron + preload + authenticated loopback engine + SQLite, disposable workspace and profile, offline scripted models
(`demo verify …` task prefixes), artifacts under `artifacts/phase7/`. Each scenario asserts DOM state, filesystem state and
persisted events; a failed assertion fails the suite.

- [x] **S1 Gate blocks an early finish.** A run edits a file and the scripted model tries to answer without testing: the  
  timeline shows the `[harness]` "run the checks" notice, `verify.required` is in the persisted `events.jsonl`, the run is  
  still running, and it finishes only after the scripted `pytest -q` returns 0. Asserting on the event log, not on prose,  
  proves the decision came from tool results. Evidence: `gate-blocked-fa.png`, event ids in `evidence.json`. — evidence
  line: "gate blocked once for pytest -q (seq 39), check at seq 42 returned 0".
- [x] **S2 Reflect loop and the exhausted card.** A fixture project fails `test_parser.py`; after 3 failed fix attempts the  
  real QuestionCard with `presentation: exhausted` appears inline and the panel shows `۳ از ۳`. Each choice gets its own  
  run: `retry` with a hint clears the counter and the hint reaches the model; `change` asks for a plan revision; `stop`  
  finishes `completed` with the changes on disk; a declined card finishes the same way. Evidence: `exhausted-fa.png`,  
  `exhausted-retry-en.png`, `stopped-fa.png`. — four evidence lines, one per choice; the hint text asserted in the
  provider request is "از جداکننده‌ی خط تیره استفاده کن".
- [x] **S3 Budget caps stop the run cleanly.** A scripted long run hits `max_steps` (lowered to 4 for the test) and a second  
  run hits `max_minutes` (1 minute through the test settings): `budget.exhausted` then `run.finished {stopped}`, no orphan  
  child process (psutil check), edits still on disk, the panel shows the reached cap. Evidence: `steps-cap-fa.png`,  
  `time-cap-fa.png`. — both caps asserted from the event log; the psutil sweep finds no surviving `ping.exe`/`pytest.exe`.
- [x] **S4 Terminal, test results and the timeout variant.** A real `pytest -q` renders read-only in the terminal with the  
  header `$ pytest -q` and its exit code, TestResults shows `۱۱ موفق` / `۱ ناموفق`, and the terminal takes no input (no  
  textarea, no `contenteditable`). A hanging command shows the red header, the kill message, and the existing  
  longer-timeout approval still works. Evidence: `terminal-fa.png`, `test-results-fa.png`, `timeout-terminal-fa.png`. — the
  timeout case also proves the retry approval still produces the 300 s command.
- [x] **S5 Ring, tooltip and popover.** Hover and keyboard focus show `۳۸٪ · ۴۸٫۸K / ۱۲۸٫۰K زمینه استفاده شده`, asserted  
  against the `context.updated` values in the event log; the arc dasharray matches the percentage; clicking opens the  
  popover with five rows, the total, the marker at 60 % and "new chat with summary" disabled until a summary exists;  
  Escape closes it and focus returns to the ring. Evidence: `ring-tooltip-fa.png`, `breakdown-fa.png`, `breakdown-en.png`. —
  the tooltip string is rebuilt from the event's `input_tokens`/`context_window`, so it asserts the arithmetic, not a
  hardcoded sentence; focus return is polled to `data-testid="context-ring"`.
- [x] **S6 Compaction fires and hands off.** With `compaction_percent` lowered for the test, a long scripted conversation  
  produces exactly one `context.summarized` notice, writes `.harness/context/summaries/<run_id>.md` (redacted, bounded),  
  the ring value drops, and "new chat with summary" starts a task whose first message carries the summary block (asserted  
  on the new run's `request.json` and events). Evidence: `compaction-fa.png`, `handoff-fa.png`. — **refined:** the 20 K
  fixture window makes this long run compact twice, so the assertion is one notice per distinct `operation_id` (and the
  timeline renders exactly that many), which is what R13 actually promises; the handoff reads the last summary, 376 bytes.
- [x] **S7 Context settings match the mock and take effect.** Section 3 renders the mock's rows, order and copy (window row  
  with `خودکار`, ۶۰٪ slider, ۸ messages, two switches); changing the threshold and saving asks for the configuration  
  approval, the approved value survives a restart, and the next run uses it (asserted through `context.summarized`  
  timing). A rejected save keeps the old value. Evidence: `settings-context-fa.png`, `settings-context-en.png`. — the saved
  45 survives a reload and the rejected 75 leaves 45 in `config.json`; the popover marker then reads the stored value.
- [x] **S8 Terminal settings match the mock and take effect.** Shell select, ۱۲۰ / ۲۰۰ fields, locked environment row  
  (`قفل · ثابت`, no input), auto/custom segment, the detected `pytest -q` / `از pyproject.toml` row, and the verify  
  switch. Changing the timeout changes the next command's timeout (asserted from `tool.call` args); turning the gate off  
  lets a scripted edit finish unverified. Evidence: `settings-terminal-fa.png`, `settings-terminal-en.png`. — a saved 30 s
  deadline appears in the next `tool.call`; with the gate off the run finishes with zero `verify.required`.
- [x] **S9 Locale, direction and layout.** The new surfaces (ring, popover, terminal, test results, both settings screens)  
  render in Persian default and remembered English at 1440×900 and 760×900, with no horizontal overflow, mirrored logical  
  spacing, LTR code/paths, Persian digits, visible focus rings and ARIA labels on the ring, popover trigger, terminal and  
  switches. Evidence: `ring-en-narrow.png`, `settings-terminal-en-narrow.png`. — asserted through
  `document.documentElement.scrollWidth <= innerWidth` plus `dir`/ARIA attributes.
- [x] **S10 Baseline regressions stay green.** `npm run test:desktop`, `tests/phase4-desktop.ts`, `tests/phase5-desktop.ts`  
  and `tests/phase6-desktop.ts` pass against the final build, with no renderer console errors, no auth regression and no  
  normal/forced lifecycle leaks. — Phase 4 (12 steps), Phase 5 (passed twice, `phase5-baseline-1.log`/`-2.log`) and Phase 6
  passed on the final build. Phase 4 exposed a real defect first: a `run_command` call owns a terminal, and the Phase 7
  command block only rendered the timeout card, so the crashed-command "interrupted" card disappeared (see
  `learnings.md`). Fixed in `activity-timeline.tsx`; the classification is now covered by `tests/unit/errors.test.ts`.

## Exit criteria

- [x] Every requirement R1–R16 has a named passing test; every automated and Electron scenario above is backed by an actual  
  result, with no unresolved spec/mock conflict. — the one refinement (S6 notice count) is recorded above and in
  `learnings.md`.
- [x] `learnings.md` records the installed APIs actually used (middleware hooks, summarizer parameters, token counter,  
  xterm version), the scripted fixture design, deviations and any remaining TODO.
- [x] `roadmap.md` updated (phase row, decisions log entries for the five decisions, Phase 8 handoff) and committed with the  
  final phase changes; every plan step has its own commit.
