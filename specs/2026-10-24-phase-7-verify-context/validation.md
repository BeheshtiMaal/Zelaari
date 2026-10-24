# Phase 7: Verify, self-correction, context ring. Validation

Every box below is automated: engine tests, UI unit tests, or a Playwright-driven Electron walkthrough against a disposable
workspace and profile with scripted offline models. Nothing depends on a human eyeballing a window.

Status: **spec written, implementation not started.** The "Final evidence" table is filled in Step 12.

## Final evidence

Filled at Step 12 from one sequential run per gate on settled source (no concurrent typecheck/build).

| Gate | Result |
| --- | --- |
| `uv run --project backend ruff check backend` | |
| `uv run --project backend mypy --strict backend` | |
| `uv run --project backend pytest backend/tests` | |
| `npm run typecheck` | |
| `npm run test:ui` | |
| `npm run generate:protocol` + `npm run generate:genui` | |
| `npm run build` | |
| `npm run build:electron` | |
| `npm run test:desktop` | |
| `tests/phase7-desktop.ts` | |

Named Phase 7 engine suites: `test_test_detection`, `test_verify_settings`, `test_test_results`, `test_verify_gate`,
`test_budget`, `test_compaction`, `test_context_breakdown`, plus the existing permission/approval/question/recovery
regressions.

Named Phase 7 UI suites: `tests/unit/context.test.ts`, `tests/unit/terminal.test.ts`, `tests/unit/verify-settings.test.ts`,
`tests/unit/run-info.test.ts`.

Artifacts: `artifacts/phase7/evidence.json` and `artifacts/phase7/*.png` (gate notice, exhausted card, timeout terminal,
test results, ring tooltip, breakdown popover, both settings screens in fa and en, narrow layout).

## Automated: engine and units

- [ ] **Gates.** `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`, `npm run test:ui` green.
- [ ] **R1** Detection matrix: custom command wins; `pytest.ini`; `pyproject.toml` mentioning pytest; `tests/` with  
  `test_*.py`; `package.json` `scripts.test`; npm's placeholder script is ignored; both runners present → pytest;  
  nothing → `none`. `test_test_detection.py`
- [ ] **R1** Detection never leaves the workspace: a symlink/junction inside `tests/` pointing outside is not followed, and  
  `.harness/`, `.git/`, `node_modules/` are skipped; the walk is bounded. `test_test_detection.py`
- [ ] **R2** Settings load/save round-trips the three sections; every out-of-range value is rejected without writing; a  
  corrupt or missing config yields the documented defaults; the write is atomic and needs the configuration approval.  
  `test_verify_settings.py`
- [ ] **R2** `GET /verify/settings` reports the live detection for the selected workspace. `test_verify_settings.py`
- [ ] **R3** The gate blocks a finish after a successful `edit_file` and allows it after a verification command returns  
  `exit_code 0`; a failed verification does not satisfy the gate. `test_verify_gate.py`
- [ ] **R3** The gate ignores denied or failed mutations, `gate: false`, and read-only mode. `test_verify_gate.py`
- [ ] **R3** The gate stops blocking after 3 consecutive injections and emits `budget.exhausted {kind: "verify"}`.  
  `test_verify_gate.py`
- [ ] **R6** With no resolvable command the gate asks through `ask_user_question` and adopts the answered command; a declined  
  card turns the gate off and emits `verify.required {blocked: false}`. `test_verify_gate.py`
- [ ] **R4** The step counter, wall clock and per-step fix attempts are real and published in `budget.updated`;  
  `max_steps` and `max_minutes` stop the run with `budget.exhausted` then `run.finished {stopped}`. `test_budget.py`
- [ ] **R5** At `fix_attempts` the exhausted card is raised on the normal barrier; `retry` injects the hint and resets the  
  counter, `change` requires a plan revision, `stop` reports once and finishes `completed`, `declined` behaves as `stop`.  
  `test_budget.py`
- [ ] **R7** `test.result` parsing: pytest summary, mocha/jest summary, unknown counts, timeout, truncated output, canary  
  secret never appears in the excerpt. `test_test_results.py`
- [ ] **R13** The summarizer receives the configured fraction and keep count; `context.summarized` is emitted once per  
  operation; the persisted summary is redacted and bounded. `test_compaction.py`
- [ ] **R14** `/runs/{id}/summary` returns the summary, 404 without one, and a seeded run carries the bounded block.  
  `test_compaction.py`
- [ ] **R12** The breakdown sums to the counted total, tool results are separate from messages, system + tools are counted,  
  skills and memory are 0, and the estimate flag is set. `test_context_breakdown.py`
- [ ] **R10** Tooltip text at 38 % / 48.8K / 128K equals the mock's string with Persian digits; estimated values get `~`;  
  0 % and over-100 % are clamped. `tests/unit/context.test.ts`
- [ ] **R11** Arc length and threshold marker position match the configured percentage; row bars are proportional.  
  `tests/unit/context.test.ts`
- [ ] **R8** Terminal payload parsing: exit code, timeout flag, line cap, unknown counts fall back to the exit code.  
  `tests/unit/terminal.test.ts`
- [ ] **R15** Settings forms map to the model, enforce the bounds, show the detection label and the shell options, and keep  
  the locked row read-only. `tests/unit/verify-settings.test.ts`
- [ ] **R16** The run panel renders real counters and the `~` estimate marker; missing events render as unavailable, not as  
  zero. `tests/unit/run-info.test.ts`
- [ ] **Wire** `src/lib/protocol.ts` is regenerated (not hand-edited) and includes `test.result`, `budget.updated`,  
  `budget.exhausted`, `verify.required`, `context.updated.breakdown` and `RunRequest.seed_summary_from`.

## Automated Windows Electron walkthroughs (`tests/phase7-desktop.ts`)

Real Electron + preload + authenticated loopback engine + SQLite, disposable workspace and profile, offline scripted models
(`demo verify …` task prefixes), artifacts under `artifacts/phase7/`. Each scenario asserts DOM state, filesystem state and
persisted events; a failed assertion fails the suite.

- [ ] **S1 Gate blocks an early finish.** A run edits a file and the scripted model tries to answer without testing: the  
  timeline shows the `[harness]` "run the checks" notice, `verify.required` is in the persisted `events.jsonl`, the run is  
  still running, and it finishes only after the scripted `pytest -q` returns 0. Asserting on the event log, not on prose,  
  proves the decision came from tool results. Evidence: `gate-blocked-fa.png`, event ids in `evidence.json`.
- [ ] **S2 Reflect loop and the exhausted card.** A fixture project fails `test_parser.py`; after 3 failed fix attempts the  
  real QuestionCard with `presentation: exhausted` appears inline and the panel shows `۳ از ۳`. Each choice gets its own  
  run: `retry` with a hint clears the counter and the hint reaches the model; `change` asks for a plan revision; `stop`  
  finishes `completed` with the changes on disk; a declined card finishes the same way. Evidence: `exhausted-fa.png`,  
  `exhausted-retry-en.png`, `stopped-fa.png`.
- [ ] **S3 Budget caps stop the run cleanly.** A scripted long run hits `max_steps` (lowered to 4 for the test) and a second  
  run hits `max_minutes` (1 minute through the test settings): `budget.exhausted` then `run.finished {stopped}`, no orphan  
  child process (psutil check), edits still on disk, the panel shows the reached cap. Evidence: `steps-cap-fa.png`,  
  `time-cap-fa.png`.
- [ ] **S4 Terminal, test results and the timeout variant.** A real `pytest -q` renders read-only in the terminal with the  
  header `$ pytest -q` and its exit code, TestResults shows `۱۱ موفق` / `۱ ناموفق`, and the terminal takes no input (no  
  textarea, no `contenteditable`). A hanging command shows the red header, the kill message, and the existing  
  longer-timeout approval still works. Evidence: `terminal-fa.png`, `test-results-fa.png`, `timeout-terminal-fa.png`.
- [ ] **S5 Ring, tooltip and popover.** Hover and keyboard focus show `۳۸٪ · ۴۸٫۸K / ۱۲۸٫۰K زمینه استفاده شده`, asserted  
  against the `context.updated` values in the event log; the arc dasharray matches the percentage; clicking opens the  
  popover with five rows, the total, the marker at 60 % and "new chat with summary" disabled until a summary exists;  
  Escape closes it and focus returns to the ring. Evidence: `ring-tooltip-fa.png`, `breakdown-fa.png`, `breakdown-en.png`.
- [ ] **S6 Compaction fires and hands off.** With `compaction_percent` lowered for the test, a long scripted conversation  
  produces exactly one `context.summarized` notice, writes `.harness/context/summaries/<run_id>.md` (redacted, bounded),  
  the ring value drops, and "new chat with summary" starts a task whose first message carries the summary block (asserted  
  on the new run's `request.json` and events). Evidence: `compaction-fa.png`, `handoff-fa.png`.
- [ ] **S7 Context settings match the mock and take effect.** Section 3 renders the mock's rows, order and copy (window row  
  with `خودکار`, ۶۰٪ slider, ۸ messages, two switches); changing the threshold and saving asks for the configuration  
  approval, the approved value survives a restart, and the next run uses it (asserted through `context.summarized`  
  timing). A rejected save keeps the old value. Evidence: `settings-context-fa.png`, `settings-context-en.png`.
- [ ] **S8 Terminal settings match the mock and take effect.** Shell select, ۱۲۰ / ۲۰۰ fields, locked environment row  
  (`قفل · ثابت`, no input), auto/custom segment, the detected `pytest -q` / `از pyproject.toml` row, and the verify  
  switch. Changing the timeout changes the next command's timeout (asserted from `tool.call` args); turning the gate off  
  lets a scripted edit finish unverified. Evidence: `settings-terminal-fa.png`, `settings-terminal-en.png`.
- [ ] **S9 Locale, direction and layout.** The new surfaces (ring, popover, terminal, test results, both settings screens)  
  render in Persian default and remembered English at 1440×900 and 760×900, with no horizontal overflow, mirrored logical  
  spacing, LTR code/paths, Persian digits, visible focus rings and ARIA labels on the ring, popover trigger, terminal and  
  switches. Evidence: `ring-en-narrow.png`, `settings-terminal-en-narrow.png`.
- [ ] **S10 Baseline regressions stay green.** `npm run test:desktop`, `tests/phase4-desktop.ts`, `tests/phase5-desktop.ts`  
  and `tests/phase6-desktop.ts` pass against the final build, with no renderer console errors, no auth regression and no  
  normal/forced lifecycle leaks.

## Exit criteria

- [ ] Every requirement R1–R16 has a named passing test; every automated and Electron scenario above is backed by an actual  
  result, with no unresolved spec/mock conflict.
- [ ] `learnings.md` records the installed APIs actually used (middleware hooks, summarizer parameters, token counter,  
  xterm version), the scripted fixture design, deviations and any remaining TODO.
- [ ] `roadmap.md` updated (phase row, decisions log entries for the five decisions, Phase 8 handoff) and committed with the  
  final phase changes; every plan step has its own commit.
