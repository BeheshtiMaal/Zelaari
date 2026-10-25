# CodeHarness

A local coding assistant for Windows that runs on your machine and asks before it touches
anything. Persian (RTL) is the default interface; English is one switch away.

It ships with an offline demo model, so you can see a real tool call and a real answer
before you own a key.

![The task screen after a run](docs/screenshots/run.png)

## Install

1. Download `CodeHarness-Setup-0.1.0.exe` (or `CodeHarness-0.1.0-x64.zip` to keep it
   portable — unzip anywhere and run `CodeHarness.exe`).
2. Run it. Windows shows **"Windows protected your PC"** because the installer is not
   code-signed. Click **More info**, then **Run anyway**.
   ![SmartScreen: More info, then Run anyway](docs/screenshots/smartscreen.png)
3. Choose a folder — the default per-user location needs no administrator rights — and
   finish.

Nothing else is required: **no Python, no Node, no build tools.** The engine is inside the
app, and the installer puts it there.

## First run

1. Pick a project folder, or click **Sample project** to open the bundled one. It carries a
   project skill (`read-framework-docs`) that starts switched off, because a project skill
   should be a deliberate choice.
2. Leave the model on **demo**. It answers offline and calls the same tools a real model
   does.
3. Ask: `read README.md and summarize`. You should see a tool line, then an answer quoting
   your file.

![The schedule screen](docs/screenshots/schedule.png)

## Add a model

Settings › Models › **Add**. Choose a preset (or type a base URL), paste the key, and press
**Test**. Keys are encrypted with the Windows data-protection API (DPAPI) in app user-data
`vault.json`; the engine receives them in memory and never writes them down. Editing a model
with a blank key keeps the old one. The Test button is the only thing that talks to a
provider before you run a task.

## Add a skill

Customize › Skills. A skill is a folder with a `SKILL.md`; put it in
`%APPDATA%\CodeHarness\skills\` for every project, or in `<your project>\.harness\skills\`
for one. Skills are **not** pasted into every prompt: the model sees their names and asks
for a body with `load_skill` when it needs one, and the timeline shows when that happened.

## Add a schedule

Schedule › **New**. A schedule is a saved task plus a recurrence. It only runs while the app
is open — that is the product rule, not a limitation. An occurrence that fell due while the
app was closed is **offered** when you next open it; nothing starts on its own. The
permission ceiling is part of the schedule, and an unattended run defaults to read-only with
a report.

## How it fits together

```
┌────────────────────────────────────────────────────────────┐
│ CodeHarness.exe  (Electron)                                │
│  ├─ renderer: the Next.js export, over app://codeharness   │
│  └─ main: spawns the watchdog, holds the per-launch token  │
└───────────────────────────┬────────────────────────────────┘
                            │ stdin: {"token", "app_data"}
                  ┌─────────▼─────────┐
                  │ watchdog.exe      │  kill-on-close job
                  └─────────┬─────────┘
                            │
                  ┌─────────▼──────────────────────────────┐
                  │ engine.exe (PyInstaller onedir)        │
                  │  FastAPI on 127.0.0.1:<random port>    │
                  │  bearer token required on every route  │
                  │  ├─ agent: deepagents + LangGraph      │
                  │  ├─ tools: jail, files, commands, git  │
                  │  └─ permissions: modes, rules, approval│
                  └────────────────────────────────────────┘
```

The token is generated per launch, kept in the Electron main process, and required by every
route including `/health`. The engine binds loopback only. Closing the window ends the
watchdog's job, which ends the engine and anything it started.

The engine also runs on its own from `backend/` with `python -m server` and a token on
stdin; `python -m server --dev` disables auth for local development. Both bind
`127.0.0.1` on an OS-assigned port.

## The eval suite

```powershell
cd backend
uv run --project . python -m evals
```

Twenty deterministic cases through the real engine — jail escapes, risky commands, the plan
gate, the verify gate, the reflect-loop budget, approvals, allow rules, skill disclosure,
questions, crash and resume, an unattended read-only run, and a malformed UI payload. It
writes `backend/evals/report.md` and exits non-zero on a failure. Live models are a written
checklist (`backend/evals/live-checklist.md`), not a skipped test that pretends to be
coverage.

## Checks

```powershell
cd backend; uv run --project . ruff check . ../scripts
uv run --project backend mypy --strict backend
npm run test:engine        # pytest
npm run typecheck          # tsc --noEmit
npm run test:ui            # theme, logical CSS and i18n contracts
npm run build; npm run build:electron
npm run test:desktop       # Playwright against the checkout
npm run desktop:build      # export + Electron + PyInstaller engine
npm run package            # NSIS installer and portable zip into dist/
uv run --project backend python scripts/smoke-installer.py dist/win-unpacked
npx tsx tests/phase10-desktop.ts
```

Run the engine tests before the UI tests: they generate a real event log for the replay
test. Desktop walkthroughs drive the real app and save screenshots and sanitized evidence
under the ignored `artifacts/`. Symlink tests need Windows Developer Mode or symlink
privileges; they never skip the containment check itself.

## Limits, honestly

Read [`SECURITY.md`](SECURITY.md) before you point this at anything you care about. The short
version: there is no sandbox. The permission layer stops the assistant from doing things you
would not have approved; it does not stop a program you approved from doing anything at all.
Work in a folder you can restore from version control.

## Development

Install Node 24 and uv, then:

```powershell
uv sync --project backend --frozen
npm ci
npm run generate:protocol
npm run generate:genui
npm run desktop          # export, bundle, open
```

`npm run desktop:build` additionally builds the PyInstaller engine; `npm run package`
produces the installer. `npm run icon` regenerates `build/icon.ico` from code, so no drawing
tool is needed. MIT; design inspired by onboard-harness, with no code copied from that AGPL
project.
