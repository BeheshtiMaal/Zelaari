# CodeHarness

A local Windows desktop coding assistant. MIT; design inspired by
onboard-harness, with no code copied from that AGPL project.

Phase 2 adds model settings, Windows-encrypted keys, remembered language switching,
recent workspaces and task replay. Select a project folder and a tested model (or
the offline demo), ask to read `README.md`, and see a real deepagents tool call and
streamed OpenUI summary with token usage. Persian RTL/dark is the default. Tools
still allow reads only; writes and commands arrive in Phase 3.

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

Switch Persian/English in Settings > Appearance and language. The choice survives
restart. Other Appearance controls are deferred.

## Optional live model

Open Settings > Models and keys > Add model. Enter a display name, Base URL,
API key and exact model name, then test tool calling before selecting/defaulting
the model. Anthropic's preset/hostname selects native Anthropic; other endpoints
use OpenAI compatibility. Jev/Metis remain disabled until URLs are supplied.

Keys are encrypted with Electron safeStorage (DPAPI) in app user-data `vault.json`;
the engine receives them in memory. Editing with a blank key retains it. Encryption
failure prevents saving. `catalog.json` contains nonsecret model/settings/workspace
metadata; run logs/checkpoints remain in the project's `.harness/` folder.

The desktop no longer imports Phase 1 environment/file credentials and leaves
existing external files untouched. The explicitly invoked live-check script may
still use these three variables or this external file:

```text
%APPDATA%\CodeHarness\phase1-provider.env
```

```dotenv
CODEHARNESS_BASE_URL=
CODEHARNESS_MODEL=
CODEHARNESS_API_KEY=
```

Fill all values using your provider's actual configuration. `uv run --project backend python
scripts/check_live.py` checks a real tool call without printing provider errors
or saving credentials. Never put credentials in the workspace. Phase 2 live
acceptance checks remain open until explicitly performed.

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
node_modules/.bin/tsx tests/phase2-desktop.ts
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
for Phase 1 results and [Phase 2 validation](specs/2026-10-19-phase-2-models-workspace/validation.md)
for current evidence and pending checks.
