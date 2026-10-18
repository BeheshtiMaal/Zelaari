# CodeHarness

A local Windows desktop coding assistant. MIT; design inspired by
onboard-harness, with no code copied from that AGPL project.

Phase 1 provides an offline, read-only walking skeleton: select a project folder,
ask to read `README.md`, and see a real deepagents tool call and streamed OpenUI
summary. The default interface is Persian RTL and dark. Later navigation and
editing controls are visibly disabled.

## Development (Windows x64)

Install Node 24 and uv, then from the repository root:

```powershell
uv sync --project backend --frozen
npm ci
npm run generate:protocol
npm run generate:genui
npm run desktop
```

`desktop` exports Next.js and builds Electron before opening the app. Python 3.12
is managed by uv. `npm run dev` starts the optional browser development server;
the complete authenticated flow runs in Electron. `npm run desktop:preview`
reopens the existing export. `npm run desktop:build` also bundles the engine and
watchdog with PyInstaller; installers arrive in Phase 10.

For English development preview, set `$env:CODEHARNESS_LANGUAGE='en'` before
launching; the exported page also supports `?lang=en`. The Settings language
switch arrives in Phase 2.

## Optional live model

Use the three environment variables `CODEHARNESS_BASE_URL`, `CODEHARNESS_MODEL`,
and `CODEHARNESS_API_KEY`, or create this file **outside the repository**:

```text
%APPDATA%\CodeHarness\phase1-provider.env
```

```dotenv
CODEHARNESS_BASE_URL=
CODEHARNESS_MODEL=
CODEHARNESS_API_KEY=
```

Fill all values using your provider's actual configuration and launch the app.
Choose the configured model in the composer. `uv run --project backend python
scripts/check_live.py` checks a real tool call without printing provider errors
or saving credentials. Phase 2 replaces this temporary configuration with the
model dialog and Windows safeStorage. Never put credentials in the workspace.

## Checks

```powershell
uv run --project backend ruff check --config backend/pyproject.toml backend scripts
uv run --project backend mypy --strict backend
npm run test:engine
npm run typecheck
npm run test:ui
npm run build
npm run build:electron
npm run test:desktop
```

Run engine tests before UI tests: they generate a real event log for the replay
test. Desktop tests drive the actual Electron app and save screenshots and
sanitized evidence under ignored `artifacts/`. Real symlink tests require Windows
Developer Mode or symlink creation privileges; they never skip containment checks.

The engine can run independently from `backend/` with `python -m server` and a
token supplied on stdin. `python -m server --dev` explicitly disables auth for
local development; both modes bind only `127.0.0.1` on an OS-assigned port.

See [SECURITY.md](SECURITY.md) for the resolve-based jail and process lifetime
limitations, and the phase's [validation](specs/2026-10-18-phase-1-walking-skeleton/validation.md)
for verified results and pending checks.
