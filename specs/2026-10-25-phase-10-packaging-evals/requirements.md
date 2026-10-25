# Phase 10: Packaging and evals. Requirements

## Goal
A Windows installer anyone can run, with proof that it works: the engine bundled so the machine needs no Python and
no Node, an NSIS per-user installer and a portable zip, a CI job that produces both, a deterministic eval suite that
states what the harness actually does, and honest documentation of what it does not protect.

## What already exists (verified before writing this spec)
- `scripts/build-engine.ps1` builds **onedir** PyInstaller bundles for `watchdog` and `engine` into `build/engine/`,
  and `build/engine/engine/engine.exe` + `build/engine/watchdog/watchdog.exe` are present.
- `scripts/check_packaged.py` starts the bundled pair, asserts **no `python.exe` child**, token auth, a demo run over
  the real event stream, and a clean watchdog shutdown.
- `electron-builder.json` exists but has **no `win` block**: no NSIS target, no zip target, no icon.
- `.github/workflows/checks.yml` runs every gate **but builds no artifact**.
- `backend/evals/` contains only `__init__.py`. `docs/screenshots/` is empty.
- `README.md` still describes Phase 2 ("tools still allow reads only"). `SECURITY.md` says the same.

## In scope
- The bundled engine carrying everything it needs at run time, including the sample project.
- electron-builder configuration, icon, NSIS per-user installer and portable zip, unsigned (D4).
- An installer smoke test that runs against the **installed** tree, not the repo.
- A CI job that produces both artifacts and uploads them.
- `backend/evals/`: ~20 deterministic cases on the demo model, plus a live-model checklist and a report file.
- `README.md` and `SECURITY.md` rewritten to describe the shipped product.
- A screenshot per mock file, taken from the real app, into `docs/screenshots/`.

## Out of scope
- Code signing, notarisation, auto-update, telemetry, macOS/Linux installers (mission non-goals).
- A hosted marketplace, accounts, payments.
- Running the evals against live providers in CI: no key belongs in CI, so live coverage stays a manual checklist.
- New product features. If packaging exposes a defect, it is fixed and recorded; nothing is added.

## Packaging
- **R1 The bundled engine carries the sample project.** `build-engine.ps1` copies `examples/` next to `engine.exe`,
  which is the layout `appdata/sample.py` already looks for (`Path(sys.executable).parent / "examples" / NAME`).
  Today nothing copies it, so a packaged app answers `404 This build does not include the sample project` — the
  docstring in `sample.py` describes a step that was never written.
- **R2 No Python and no Node on the user's machine.** The app starts the bundled `engine.exe` under the bundled
  `watchdog.exe`; neither the app nor the engine spawns `python.exe`, `pythonw.exe`, `node.exe` or `npm`. The
  packaged tree contains no interpreter outside the bundle.
- **R3 electron-builder produces exactly two artifacts** in `dist/`: an NSIS installer and a portable zip. Both are
  unsigned, and neither is produced by any other step.
- **R4 The installer is per-user.** It installs without elevation into `%LOCALAPPDATA%\Programs\CodeHarness`, creates
  a Start-menu entry, and its uninstaller removes the program **without** touching app data.
- **R5 The app has an icon.** `build/icon.ico` with at least a 256×256 image, used by the window, the installer, the
  shortcut and the uninstaller.
- **R6 The installed tree is self-contained.** `out/` (renderer), `build/engine/` (engine + watchdog), the sample
  project, the bundled skills and `agent/genui_prompt.txt` all live inside it; nothing resolves back into a checkout.
- **R7 The version is 0.1.0 everywhere**: `package.json`, both artifact filenames, the About screen.

## Proof that it works
- **R8 An installer smoke test runs against the installed tree.** It takes the path of an installed (or unpacked)
  app, launches the real executable, and asserts: the engine answers, the token is required, a demo run completes
  with a real tool result, the sample project opens and contains the `read-framework-docs` skill, and the window
  closes cleanly.
- **R9 No orphan processes after quit.** Closing the app leaves no `engine.exe` or `watchdog.exe` behind, including
  when the window is closed while a run is in flight.
- **R10 No secrets in the packaged app or its logs.** The installed tree, `logs/main.log` and every `events.jsonl`
  contain no API key, no bearer token, and no fixture token.

## CI
- **R11 CI produces the artifacts.** A job runs the gates, builds the engine, builds both artifacts with
  electron-builder and uploads them. A failure in any gate fails the job; the artifacts are not built from a tree
  that has not passed.

## Evals
- **R12 An eval suite exists and runs in one command.** `backend/evals/` runs through the engine's own `RunManager`
  (no second execution path), covers the brief's nine areas, and writes a report file. It exits non-zero when a case
  fails.
- **R13 The eval suite is offline.** No network, no key, no telemetry; it runs on the demo model in CI.
- **R14 Each case asserts on what the engine did**, not on what a model said: tool results, approval records, rule
  decisions, event types, budget counters.
- **R15 A live-model checklist exists** for one OpenAI-compatible model and one Anthropic model, as manual steps with
  the exact task and the expected visible outcome.

## Documentation
- **R16 `README.md` describes the shipped product**: what it is, how to install (including the SmartScreen
  "More info → Run anyway" step), first run, an architecture diagram, how to add a model, how to add a skill, how to
  add a schedule, how to run the evals and the gates. Screenshots come from the real app.
- **R17 `SECURITY.md` states the honest limits**: there is no sandbox; what the permission layer, the jail, the token
  and the vault do protect; what they do not; and what a person should not do with this app. No stale phase claims.
- **R18 Every mock screen is compared once.** One screenshot per file in `docs/mock-source/` (18), stored in
  `docs/screenshots/`, with a table naming each deliberate deviation and why.

## Manual
- **R19 The clean-machine test.** On a machine that has never run this project: install, add a key, pick a folder,
  fix a failing-test task in under five minutes; every dangerous action shows an approval card; rejecting one never
  crashes the app.

## Decisions
- **D45 The installer is assisted and per-user.** `oneClick: false`, `perMachine: false`, `allowElevation: false`:
  the person sees an install page and can choose a folder, and nothing ever asks for administrator rights. A
  one-click installer is faster but gives no way to see where the app went, and a per-machine install needs UAC on a
  machine whose owner may not be the admin.
- **D46 The eval suite drives the real engine.** Cases call `RunManager` and read `events.jsonl`, the same path the
  app uses. A suite that reimplements the loop would pass while the product failed.
- **D47 Live models stay a checklist.** CI has no key and must not have one, so live coverage is a written manual
  procedure with a fixed task and expected outcome, not a skipped test that pretends to be coverage.
- **D48 Screenshots are generated, not pasted.** A walkthrough script captures them into `docs/screenshots/` so they
  can be regenerated after any visual change; a hand-cropped image is a screenshot of a version that no longer exists.
- **D49 The sample ships inside the engine bundle, not as a separate resource.** `extraResources` would put it beside
  `engine.exe` in one layout and beside `app.asar` in another; copying it into `build/engine/engine/` keeps the one
  lookup `sample.py` already performs.

## Open questions
1. **Installer UX** — assisted per-user (recommended, D45) or one-click. One-click is one fewer screen; assisted
   shows where the app goes and allows another folder.
2. **The clean-machine test (R19)** — I have no fresh VM here. Do you run it on your machine from my checklist, or do
   we accept "a fresh Windows user profile on this machine" as the substitute and record that it is weaker?
3. **Screenshot language** — Persian only (the product default) for all 18, or both languages for the shell screens
   and Persian for the rest? Both everywhere doubles the set to 36 images for a README that shows about eight.
