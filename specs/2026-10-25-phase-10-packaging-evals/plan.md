# Phase 10: Packaging and evals. Plan

Work top to bottom. One commit per step, gates green before moving on. Steps 1–2 are the only ones that change how
the product is built; 3–4 prove it; 5–8 document it.

## Step 1: The engine bundle carries what it needs
- `scripts/build-engine.ps1`: after the engine build, copy `examples/` to `build/engine/engine/examples/` (the layout
  `appdata/sample.py` already looks for) and fail the build if `examples/sample-project/README.md` is missing from the
  output. `sample.py`'s docstring already claims this step exists; this makes it true.
- `backend/tests/test_sample_bundle.py`: `sample.source()` resolves the packaged layout (a temporary tree with
  `engine.exe` + `examples/sample-project/README.md`) as well as the checkout layout, and returns `None` for a tree
  with neither; `materialise` copies once and never overwrites an edited copy.

Commit: `build(engine): ship the sample project inside the bundle, where sample.py looks for it`

## Step 2: electron-builder produces both artifacts
- `npm i -D electron-builder@26.18.0` (verified current on the registry; NSIS binaries are fetched from GitHub, which
  is reachable — recorded in `learnings.md` with the exact version).
- `build/icon.ico`: 256/128/64/48/32/16, generated from a small SVG with the product's accent colour and a
  `>_`-shaped mark, checked in so a build never depends on ImageMagick being installed.
- `electron-builder.json`: `win.target = [nsis, zip]`, `nsis.oneClick = false`, `perMachine = false`,
  `allowElevation = false`, `shortcutName`, `artifactName` for both targets, `win.icon`.
- `package.json`: `"package": "electron-builder --win --publish never"` and `"package:dir": "electron-builder --win --dir"`
  (the second one produces an unpacked tree for the smoke test without NSIS).

Commit: `build(package): an icon, an NSIS installer and a portable zip at version 0.1.0`

## Step 3: The installer smoke test
- `scripts/smoke-installer.py`: takes a path (an installed folder or `dist/win-unpacked`), starts the real
  `CodeHarness.exe`, waits for the window's engine to answer, asserts token auth, opens the sample project, runs one
  demo task through the app's own client, asserts a real tool result, closes the window, and asserts no
  `engine.exe`/`watchdog.exe` survives. Reuses `psutil` and `httpx` the way `check_packaged.py` does.
- It also scans the tree it was given for a Node runtime and for any `*.key`/`API_KEY` string, and asserts
  `logs/main.log` carries no bearer token.
- `tests/phase10-desktop.ts`: launches the **unpacked build** through Playwright (`executablePath`), asserts the
  Persian first run, the demo model with no key, the sample project with `read-framework-docs`, a demo run, and a
  clean quit with no surviving processes.

Commit: `test(package): smoke the installed app, not the checkout`

## Step 4: CI builds the artifacts
- `.github/workflows/checks.yml`: keep the gate job; add a `package` job that needs it, runs
  `npm run desktop:build`, `npm run package`, and uploads `dist/*.exe` and `dist/*.zip` with
  `actions/upload-artifact@v4`, plus `scripts/smoke-installer.py dist/win-unpacked`.
- Pin the version check: the workflow asserts `package.json`'s version is `0.1.0` and that both artifacts exist.

Commit: `ci: build the installer and the zip from a tree that passed the gates`

## Step 5: The eval suite
- `backend/evals/harness.py`: a `Case` (name, area, task, workspace fixture, expectations) and a runner that starts a
  real `RunManager` in a temporary workspace, drives one run, and hands the case the events plus the final catalog
  state.
- `backend/evals/cases.py`: ~20 cases across the brief's nine areas — jail escape (absolute path, `..`, symlink out),
  risky command classification and escalation, always-ask list in auto mode, plan gate threshold, deviation gate,
  verify gate, reflect-loop budget exhaustion, approval approve/edit/reject, allow-rule from "don't ask again",
  skill disclosure (`load_skill` only on demand), question flow (single/multi/Other/declined), crash and resume
  (no replay of an in-flight command), schedule unattended read-only, and a render_ui fallback.
- `backend/evals/__main__.py`: `python -m evals` runs every case, prints a table, writes `backend/evals/report.md`
  and `backend/evals/report.json`, exits 1 if any case fails.
- `backend/evals/live-checklist.md`: one OpenAI-compatible and one Anthropic model, same task, expected visible
  outcome, what to look for in the timeline.
- `backend/tests/test_evals.py`: the suite runs green offline, every case name is unique, and the report is written.

Commit: `feat(evals): twenty deterministic cases through the real engine, and a report`

## Step 6: README and SECURITY.md
- `README.md` rewritten for the shipped product: what it is, install + SmartScreen, first run, architecture diagram
  (ASCII, matching the tech stack's shape), add a model, add a skill, add a schedule, the eval suite, the gates,
  the limits. Screenshots referenced from `docs/screenshots/`.
- `SECURITY.md` rewritten: no sandbox, what the jail/token/vault/permission layer do, what they do not, what a person
  should not do with this app.

Commit: `docs: the README and SECURITY.md describe the app that ships`

## Step 7: Every mock screen, once
- `tests/phase10-screens.ts`: for each of the 18 files in `docs/mock-source/`, drive the real app to that screen and
  capture `docs/screenshots/<name>.png` at a fixed 1440×960. Reuses the navigation the phase walkthroughs already
  know; no new app code.
- `docs/screenshots/README.md`: the table — mock file, screenshot, deliberate deviations with the decision that made
  them.

Commit: `docs(screens): one screenshot per mock file, with the deviations named`

## Step 8: Record and roadmap
- Tick `validation.md` with the test or artifact that proves each box; write `learnings.md`; mark roadmap row 10
  complete, add D45–D49, and write the handoff (there is no Phase 11: what a future maintainer inherits).

Commit: `test(phase10): the record, the roadmap, and the handoff`

## Ordering rules
- Step 3 needs Steps 1–2 (there is nothing to smoke without an unpacked tree).
- Step 4 needs Step 3 (the job runs the smoke test).
- Step 5 is independent of 1–4 and can run in parallel if the machine allows.
- Steps 6–7 need a build; the screenshots need the app, not the installer, so they can precede Step 3.
