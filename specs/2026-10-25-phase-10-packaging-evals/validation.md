# Phase 10: Packaging and evals. Validation

Done only when every box is ticked with the test or the artifact that proves it.

## Automated (CI)

### The bundle (Step 1)
- [ ] R1 `sample.source()` resolves the packaged layout, the checkout layout, and returns `None` when neither has a
      sample; `test_sample_bundle.py::test_resolves_both_layouts`.
- [ ] R1 `build/engine/engine/examples/sample-project/README.md` exists after `npm run build:engine`; asserted by the
      build script itself and by `scripts/smoke-installer.py`.
- [ ] R1 `materialise` copies once and never overwrites an edited copy;
      `::test_materialise_never_overwrites`.

### The artifacts (Step 2)
- [ ] R3 `npm run package` writes exactly two files to `dist/`: one `.exe` installer and one `.zip`.
- [ ] R4 the installer's NSIS script is per-user (`perMachine: false`, `allowElevation: false`); `npm run package:dir`
      produces an unpacked tree whose `resources/` holds `out/` and `build/engine/`.
- [ ] R5 `build/icon.ico` carries a 256×256 image and is referenced by `electron-builder.json`.
- [ ] R6 the unpacked tree contains `out/index.html`, `build/engine/engine/engine.exe`,
      `build/engine/engine/examples/sample-project/README.md`, and `agent/genui_prompt.txt` inside `_internal/`.
- [ ] R7 `package.json` version is `0.1.0` and both artifact names carry it.

### Proof (Steps 3–4)
- [ ] R8 `scripts/smoke-installer.py dist/win-unpacked` passes: engine answers, 401 without the token, sample project
      opens, one demo run reaches a real tool result, the window closes.
- [ ] R9 after the smoke test's window closes, no `engine.exe` or `watchdog.exe` from that tree survives.
- [ ] R10 the smoke test finds no Node runtime, no `API_KEY` string and no bearer token in the tree or
      `logs/main.log`.
- [ ] R2 the process tree under the app contains no `python.exe`/`pythonw.exe`/`node.exe`;
      `scripts/check_packaged.py` (already green) and `tests/phase10-desktop.ts`.
- [ ] R11 the CI workflow has a job that uploads both artifacts and runs the smoke test on `dist/win-unpacked`.

### Evals (Step 5)
- [ ] R12 `uv run --project backend python -m evals` exits 0 and writes `report.md` + `report.json`;
      `test_evals.py::test_the_suite_passes`.
- [ ] R12 every case name is unique and every one of the nine areas has at least one case; `::test_covers_every_area`.
- [ ] R13 the suite makes no network call and needs no key: it runs with the `conftest.py` scrub in place.
- [ ] R14 the cases assert on engine facts — a `tool.result` text, an approval record, a rule decision, a budget
      counter, an event type — not on model prose.
- [ ] R15 `backend/evals/live-checklist.md` exists with one OpenAI-compatible and one Anthropic task, the exact
      prompt, and the expected visible outcome.

### Docs (Steps 6–7)
- [ ] R16 `README.md` mentions install, SmartScreen, first run, architecture, model, skill, schedule, evals, gates,
      and links a screenshot for each section it describes.
- [ ] R17 `SECURITY.md` states there is no sandbox, what is protected, what is not, and carries no Phase 1/2 claim.
- [ ] R18 `docs/screenshots/` holds one image per mock file (18) and `docs/screenshots/README.md` names every
      deviation with its decision.
- [ ] Every gate: `ruff`, `mypy --strict backend`, `pytest`, `npx tsc --noEmit`, `npm run test:ui`, `npm run build`,
      `npm run build:electron`, `npm run build:engine`, `npm run package`, `npm run test:desktop`,
      `scripts/smoke-installer.py`.

## Manual (Windows 10/11)
- [ ] R4 the installer runs without a UAC prompt and installs under `%LOCALAPPDATA%\Programs\CodeHarness`.
- [ ] R4 uninstalling removes the program, the shortcuts and the registry entry, and leaves
      `%APPDATA%\CodeHarness` (app data) untouched.
- [ ] R16 the README's SmartScreen steps match what the installer actually shows on a machine that has never run it.
- [ ] R19 clean machine: install → add a key → pick a folder → fix a failing test in under five minutes; every
      dangerous action shows an approval card; rejecting one never crashes the app.
- [ ] R18 the screenshots match the running app at 1440×960 in both themes where the screen supports one.
- [ ] R15 one live OpenAI-compatible model and one live Anthropic model complete the checklist task.

## Exit criteria
Every box ticked with evidence, gates green, `learnings.md` written (verified versions and URLs, deviations,
surprises, open items), `roadmap.md` row 10 complete with D45–D49 and the handoff.
