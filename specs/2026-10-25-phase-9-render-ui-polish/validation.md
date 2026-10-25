# Phase 9: `render_ui` and polish. Validation

Every item is automated: engine behaviour by `pytest`, pure logic and generated artefacts by `npm run test:ui`,  
screens by a Playwright-driven Electron suite (`tests/phase9-desktop.ts`) that runs the real preload, the  
authenticated loopback engine and SQLite against a disposable workspace and profile, with offline scripted models.  
Screenshots are evidence, never the assertion. Tick a box only with the test name or the evidence line that proves it.

## Automated: engine

- [ ] R1 `genui_schema.json` and `genui_prompt.txt` are produced from `library.tsx` and regeneration is byte-identical  
  — `npm run generate:genui` run twice; `tests/unit/genui.test.ts::test_the_schema_names_every_component`
- [ ] R3 the parser accepts the documented grammar (strings with escapes, numbers, booleans, null, arrays, objects,  
  references, calls) and refuses a statement without `=` — `test_genui_parser.py`
- [ ] R3 each failure is one line with the 1-based line number: unknown component, wrong arity, wrong literal type,  
  unresolved reference, unreachable statement, duplicate identifier, bad id shape — `test_genui_validate.py`
- [ ] R3 the bounds hold: > 20 000 characters, > 200 statements and depth > 8 are refused before parsing further —  
  `test_genui_validate.py::test_size_statements_and_depth_are_bounded`
- [ ] R3 the validator never raises: a corpus of malformed programs (fuzz-shaped fixtures) always returns a problem —  
  `test_genui_validate.py::test_malformed_input_never_raises`
- [ ] R2 `render_ui` returns `{ok, components, statements}` and never the program, and is `allow` in read-only, ask and  
  auto — `test_genui_tool.py`
- [ ] R2 `render_ui` is not a mutation for the verify gate and does not consume the fix budget —  
  `test_genui_tool.py::test_render_ui_is_not_a_mutation_for_the_verify_gate`
- [ ] R4 a failed program returns the short error, emits `ui.render` with `ok: false`, and the run continues —  
  `test_genui_tool.py::test_a_bad_program_returns_an_error_and_the_run_continues`
- [ ] R4 a successful program emits exactly one `ui.render` with `ok: true` and the component names, and the event is in  
  `events.jsonl` — `test_genui_tool.py::test_a_good_program_is_persisted`
- [ ] R4 a secret inside the program's strings is redacted before the event is written —  
  `test_genui_tool.py::test_the_program_is_redacted_before_it_is_persisted`
- [ ] R5 an id the run never produced renders the component's not-found state and creates no approval, question or plan  
  — `test_genui_tool.py::test_unknown_ids_create_nothing`
- [ ] R1 `FileTree` lists the run's changed files from the action journal, not a model-supplied list —  
  `test_run_files.py`
- [ ] R7 `Settings` defaults match the mock (fa, dark, medium, three switches on, `ask`, 30 days) and round-trip through  
  `PUT /settings`; a bad value is rejected — `test_settings_preferences.py`
- [ ] R7 a saved `default_mode` is the mode of the next run created without an explicit override —  
  `test_settings_preferences.py::test_the_default_mode_reaches_a_new_run`
- [ ] R8 the always-ask list is engine-owned and identical to the one the permission middleware enforces —  
  `test_rules_routes.py::test_always_ask_matches_the_middleware`
- [ ] R8 a planning-settings change from the Permissions section is a proposal, and approving it changes the gate —  
  `test_planning_settings.py` (existing) re-asserted
- [ ] R9 `GET /data` reports the real app-data path, the `.harness` path, the run count and the oldest run —  
  `test_data_routes.py::test_summary_reports_real_paths`
- [ ] R9 `DELETE /data/runs` removes run folders, the checkpoint database and task rows, and removes no workspace file —  
  `test_data_routes.py::test_clearing_history_keeps_workspace_files`
- [ ] R9 retention deletes only runs older than the window, on startup and after a run — `test_data_routes.py`
- [ ] R10 `GET /about` reports the version in `package.json` and the licence, and matches Electron's `app.getVersion()`  
  in the walkthrough — `test_about.py`
- [ ] R12 the engine log is bounded (≤ 512 KB, one rotation), redacted and contains no prompt text, key or command  
  output — `test_engine_log.py`
- [ ] R11 `POST /workspaces/sample` materialises the bundled example inside app data and selects it; a second call  
  reuses it instead of overwriting — `test_sample_workspace.py`
- [ ] R17 the new event and models are in the generated protocol with no diff after regeneration —  
  `npm run generate:protocol` run twice, byte-identical

## Automated: UI unit

- [ ] R1 the schema declares all twelve components, every engine-state component declares only id props, and `Tabs`  
  rejects mismatched label/panel lengths — `tests/unit/genui.test.ts`
- [ ] R3 a failed render keeps the note and the model's markdown; a successful one hides the raw program —  
  same file
- [ ] R7 the appearance segment mapping, `system` resolution and font scale class are pure and correct —  
  `tests/unit/appearance.test.ts`
- [ ] R8 `RulesResponse` maps to the table rows and badges, and an unreadable grid still shows the three locked rows —  
  `tests/unit/permissions-view.test.ts`
- [ ] R9 the confirm gate enables the destructive button only after the checkbox, and the summary text names the effect  
  — `tests/unit/confirm.test.ts`
- [ ] R11 the six empty states expose their mock copy and at least one real action; the no-schedules entry is present  
  for 9b to wire — `tests/unit/states.test.ts`
- [ ] R13 both palettes define exactly the same token names, every token used in a rule is defined, no colour literal  
  exists outside the palette blocks, no raw `font-size: Npx` exists, and the documented pairs meet 4.5:1 / 3:1 in  
  both themes — `tests/unit/theme.test.ts`
- [ ] R14 the shortcut table is complete and every entry names its handler — `tests/unit/shortcuts.test.ts`
- [ ] R16 fa and en have identical keys and shapes, no empty strings, identical `{placeholders}`, no Persian in `en`,  
  no ASCII digits in `fa`, and exactly one allowed Persian literal in components — `tests/unit/i18n.test.ts`
- [ ] R15 no physical CSS property appears in `globals.css` or any TSX inline style —  
  `tests/unit/logical-css.test.ts`

## Automated: Electron walkthrough (`tests/phase9-desktop.ts`)

- [ ] S1 the four new settings sections match the mock: nav with seven sections and `aria-current`, the section cards,  
  the row labels and the control values (Persian digits) — DOM assertions plus  
  `artifacts/phase9/settings-appearance-fa.png`
- [ ] S2 the language, theme and font-size switches change the rendered shell immediately, and survive a relaunch —  
  evidence line naming the applied `data-theme` / `data-font` and the `lang`/`dir` after restart
- [ ] S3 permissions shows the three locked rows, the rules table with its badges, and a threshold change appears as a  
  pending review that only applies after approval
- [ ] S4 data shows the resolved app-data path, retention persists, and clearing history needs the dialog **and** the  
  checkbox; cancelling leaves every run folder in place
- [ ] S5 about shows the version that Electron reports and `باز کردن پوشه‌ی لاگ` opens the log directory
- [ ] S6 a `demo render` run renders the composed program (the expected `data-testid` nodes are in the DOM) and the  
  persisted `ui.render` event reconstructs it on replay; a malformed program falls back with the error note and the  
  run continues to a normal answer
- [ ] S7 killing the engine process shows the crash card, `راه‌اندازی دوباره` restarts it and the task reopens  
  interrupted with no replayed command, and `مشاهده‌ی لاگ` opens the folder
- [ ] S8 light theme, large font and English LTR all render with no horizontal overflow at 1440×960, and the sidebar  
  mirrors to the left in LTR

## Automated: gates

Run in this order on the settled source (`scripts/desktop-gates.sh` runs the desktop half and writes one log per suite  
into `artifacts/phase9/`). `npm run build` must precede any desktop suite, because Electron serves `out/`.

- [ ] `ruff check backend` — All checks passed
- [ ] `mypy --strict backend` — 0 errors
- [ ] `pytest backend/tests` — all pass, log in `artifacts/phase9/pytest.log`
- [ ] `tsc --noEmit`
- [ ] `npm run test:ui`
- [ ] `npm run generate:protocol` and `npm run generate:genui` leave no diff
- [ ] `npm run build`
- [ ] `npm run build:electron`
- [ ] `npm run test:desktop` (baseline shell)
- [ ] `tests/phase2-desktop.ts` … `tests/phase8-desktop.ts` still pass on the settled build
- [ ] `tests/phase9-desktop.ts` — S1–S8 in one sequential run, `artifacts/phase9/desktop-phase9.log`

## Manual checks (performed once, recorded here)

- [ ] Every screen in the six mocks is compared side by side with the running app in Persian RTL, and the differences  
  are either fixed or written into `learnings.md`
- [ ] The light theme is walked through home, run, inbox, customize and all seven settings sections, looking for  
  unreadable text or an untokenised surface
- [ ] Tab order is walked from the top of home, a run, the inbox and a dialog, and recorded as a short list
- [ ] A screen reader pass (Windows Narrator) on the approval card, the question card and the crash screen: each  
  announces its title, its state and its actions
