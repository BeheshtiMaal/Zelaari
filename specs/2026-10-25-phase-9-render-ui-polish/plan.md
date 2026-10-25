# Phase 9: `render_ui` and polish. Plan

One commit per step. Steps 1–3 are the GenUI path (library → validator → renderer), 4–6 are Settings, 7–8 are the
visual system and the states, 9 is accessibility and copy, 10 is wire, walkthrough, gates and docs. Every step ends
with its tests written and the gates it can affect re-run.

## Step 1: Complete the library and generate its contract
- `src/genui/library.tsx`: add `TerminalPanel`, `TestResults`, `FileTree`, `Tabs`, `Table`; widen `Stack.children`
  and the `Tabs.panels` union to the whole library; keep the id-only rule for engine-state components and note it in
  each description.
- New components live in `src/genui/components/`: `terminal.tsx` (reuses `TerminalPanel`/`TestResults` from
  `src/components/terminal/`), `file-tree.tsx` (reads the run's changed files), `tabs.tsx` (tab bar with
  Arrow/Home/End, `role="tablist"`, panels labelled by their tabs), `table.tsx` (columns + rows, `dir="auto"` cells).
- `scripts/generate-genui.tsx`: also write `backend/agent/genui_schema.json` from `library.toJSONSchema()`.
- `src/lib/use-run-files.ts`: `GET /runs/{id}/files` (changed paths from the action journal) for `FileTree`.
- Tests: `tests/unit/genui.test.ts` — the schema names all twelve components, every engine-state component declares
  only id props, `Tabs` label/panel lengths must match, and the generator output is stable.

## Step 2: The Python validator and the `render_ui` tool
- `backend/genui/schema.py`: load and cache `agent/genui_schema.json` into a typed `LibrarySchema`
  (components → ordered props → required flag → literal kind → `anyOf` refs).
- `backend/genui/parser.py`: tokeniser and recursive-descent parser for the bounded grammar (strings with escapes,
  numbers, booleans, null, arrays, objects, references, calls) with line numbers and hard depth/size limits.
- `backend/genui/validate.py`: `validate(text) -> Program | Problem`, every R3 check, one-line errors, no exceptions.
- `backend/genui/tool.py`: the `render_ui` tool (args `{ui}`), emitting `ui.render` on the bus and returning the short
  result; `backend/genui/prompt.py`: the preamble + generated prompt, bounded to 8 000 characters.
- `backend/permissions/rules.py`: `ui` category, `render_ui` allowed in every mode; `backend/verify/gate.py`: assert
  `render_ui` is not a mutation; `backend/agent/factory.py`: register the tool and append the rendering section to the
  system prompt; `backend/agent/events.py`: the `ui.render` event.
- Tests: `test_genui_parser.py` (grammar, escapes, nesting, bounds), `test_genui_validate.py` (unknown component, wrong
  arity, wrong literal type, unresolved reference, unreachable statement, bad id, depth, size — each with its line
  number), `test_genui_tool.py` (ok result shape, failure result is short and the run continues, redaction, not a
  mutation, allowed in read-only), `test_genui_prompt.py` (the prompt is generated, bounded, and names every
  component).

## Step 3: Render a program in the timeline
- `src/store/run.ts`: a `{kind: "ui"}` timeline item from `ui.render`, carrying `ok`, `text`, `error` and `call_id`.
- `src/components/genui/ui-block.tsx`: renders `Message` on success and, on failure, the model's markdown plus an
  inline note with the error (`role="status"`, `data-testid="ui-fallback"`).
- `src/lib/timeline.ts`: ordering so a `ui.render` sits with its tool call.
- Tests: `tests/unit/genui.test.ts` extended — reducer places the block, a failed render keeps the note and the
  markdown, a successful one hides the raw program.

## Step 4: Settings frame, appearance and the app preferences
- `backend/providers/base.py`: `Settings` gains `default_mode`, `appearance` (`theme`, `font`, `show_thinking`,
  `keep_thinking_open`, `show_terminal`) and `retention_days`; `backend/store/catalog.py` validates and persists them
  (defaults from the mock); `PUT /settings` keeps rejecting an untested `default_model`.
- `src/components/settings/settings-frame.tsx` + `settings-screen.tsx` refactor into seven section components
  (`models-section.tsx` extracted unchanged in behaviour).
- `src/components/settings/appearance-section.tsx`, `src/i18n/settings.ts` (fa from the mock, en equivalents),
  `src/lib/use-appearance.ts` (theme/font applied to `<html>` before paint, activity switches).
- `src/components/planning/activity-timeline.tsx` honours the three activity switches.
- Tests: `test_settings_preferences.py` (defaults, round-trip, rejection of a bad value), `tests/unit/appearance.test.ts`
  (segment mapping, theme resolution for `system`, font scale class).

## Step 5: Permissions and safety
- `src/components/settings/permissions-section.tsx`: default mode, plan gate switch + thresholds (reuses
  `usePlanningSettings` and the pending-approval card), locked always-ask rows from `GET /rules.always_ask`, and the
  rules table from the effective grid.
- `src/lib/permissions-view.ts`: pure mapping of `RulesResponse` → table rows and badges, and the fail-closed locked
  list.
- Tests: `tests/unit/permissions-view.test.ts` (row mapping, badge per decision, fail-closed list, no editable locked
  row).

## Step 6: Data and privacy, About, and the new engine/Electron surface
- `backend/server/data.py`: `GET /data` (`DataSummary`), `DELETE /data/runs` (run folders, checkpoints, task rows,
  bounded and counted); `backend/store/catalog.py`: retention applied on startup and after a run.
- `backend/server/about.py`: `GET /about` (`AppInfo`).
- `electron/main.ts`: `app-info`, `reveal-app-data`, `open-log-folder`, `clear-keys`, and the log directory;
  `electron/sidecar.ts`: keep a bounded `main.log` line per start/exit; `electron/preload.ts` + `src/lib/desktop.ts`:
  the new bridge methods.
- `src/components/settings/data-section.tsx`, `about-section.tsx`, `src/components/settings/confirm-dialog.tsx`
  (Radix Dialog, names the effect, `می‌دانم` checkbox, destructive confirm, focus restore).
- Tests: `test_data_routes.py` (summary shape, deletion removes runs and never a workspace file, retention window,
  counting), `test_about.py` (version matches `package.json`), `tests/unit/confirm.test.ts` (confirm gate logic).

## Step 7: Tokens, light palette, type scale, sweep
- `src/app/globals.css`: palette blocks `:root` (dark) and `[data-theme="light"]`, the `--fs-*` type scale with
  `[data-font=…]` overrides, and a mechanical sweep replacing all 242 colour literals and 142 raw font sizes with
  tokens. `src/lib/theme.ts`: resolve `system`, apply before paint, persist.
- Tests: `tests/unit/theme.test.ts` — both palettes define exactly the same token names, every token used in a rule is
  defined, no colour literal outside the palette blocks, no raw `font-size: Npx`, and WCAG contrast for the documented
  text/border pairs in both themes.

## Step 8: Empty states, error states, crash and restart
- `src/components/states/empty-state.tsx` + `src/i18n/states.ts`: the six states; wire home, inbox, workspace,
  customize/skills; `backend/server/workspaces.py`: `POST /workspaces/sample`.
- `src/components/states/crash-card.tsx`: the blocking engine-crash screen; `electron/main.ts`: a sidecar exit no
  longer destroys the windows — it reports `engine-status` and offers `restart-engine`; `src/lib/use-engine.ts`
  (status, restart, re-bootstrap).
- `backend/server/logging.py`: a bounded redacted `engine.log` (512 KB, one rotation) and its wiring in
  `server/main.py`; the crash card's `مشاهده‌ی لاگ` calls `open-log-folder`.
- Tests: `test_engine_log.py` (bounded, rotated, redacted, no prompt text), `test_sample_workspace.py`,
  `tests/unit/states.test.ts` (six states' copy and actions, no-schedules reachable by the component contract).

## Step 9: Keyboard, focus, ARIA, RTL/LTR, i18n completeness
- `src/lib/shortcuts.ts` (the documented table) and its use in the composer, question card, approval card and inbox
  list; `src/components/shell/skip-link.tsx`; focus restore in `confirm-dialog` and `model-dialog`.
- `src/app/globals.css`: one focus-ring style, reduced-motion coverage for the remaining animations.
- `tests/unit/shortcuts.test.ts`, `tests/unit/i18n.test.ts` (key parity, shapes, placeholders, no Persian in `en`, no
  ASCII digits in `fa`, the single allowed Persian literal in components), `tests/unit/logical-css.test.ts` (no
  physical properties in CSS or TSX).

## Step 10: Wire, walkthrough, gates, docs
- `npm run generate:protocol` and `npm run generate:genui`; the diff is committed.
- `tests/phase9-desktop.ts`: S1 the four settings sections match the mock (nav, cards, rows, values, Persian digits);
  S2 appearance switches change the rendered shell and persist across a relaunch; S3 permissions shows the locked list
  and the rules table, and a threshold change is an approval; S4 data shows the real paths, retention persists, and the
  danger zone needs both confirmations (rejecting writes nothing); S5 about shows the version and opens the log folder;
  S6 a `demo render` run renders a real program (components asserted in the DOM) and a malformed program falls back with
  the error note while the run continues; S7 killing the engine shows the crash card, restart recovers and the task
  reopens interrupted with no replay; S8 the light theme, the font scale and the English LTR pass with no overflow.
- `backend/tests/phase9_seed.py`; `validation.md` boxes ticked with evidence; `learnings.md`; `roadmap.md` row 9, the
  decisions log (D27–D33) and the Phase 9b handoff.
