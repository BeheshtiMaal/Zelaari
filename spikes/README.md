# Phase 0 experiments

Throwaway code only. Product implementation belongs to later phases.

Prerequisites: Windows 10/11 x64, uv with Python 3.12, Node/npm, and permission
to create symlinks (Developer Mode or a suitably privileged session).

Run in this order:

1. From `spikes/python`: `uv sync --locked`, then `./build.ps1` to package both
   the engine and its Windows job watchdog.
2. From `spikes/ui`: `npm ci`, `npm run build:electron`, `npm run build`,
   `npm run typecheck`, then `npm test`. The first Electron use may download
   its executable; run `node node_modules/electron/install.js` first to isolate
   that installation from Playwright's launch timeout.
3. From `spikes/python`: `uv run ruff check .`, `uv run mypy .`, `uv run pytest -v`.

The pytest bootstrap disables inherited LangChain/LangSmith tracing and removes
API-key environment entries inside the test process. Provider tests use synthetic
HTTP transports. The demo test rejects network connections. Shell and packaged
launch tests build child environments from an allowlist.

The symlink test deliberately fails with Windows error 1314 if the required
privilege is unavailable. A deselected or skipped test is not phase completion.

`npm test` runs hidden Electron windows for both protocols. It writes screenshots
of final cards and malformed fallback, plus `openui.json`. Python tests produce
agent stream summaries, interrupt payloads, shell outcomes, and process cleanup
evidence in `spikes/artifacts/`. These contain synthetic fixture data and no tokens.

The sidecar launch harness receives an ephemeral `SPIKE_TOKEN` environment value
from pytest, immediately deletes it before creating children, and hands it to the
packaged watchdog and engine through stdin pipes. The engine's authenticated
`POST /quit` endpoint exists only for this experiment; it asks Electron to perform
a normal `app.quit()`. Force-kill tests kill only Electron main and observe cleanup.

Generated artifacts are ignored. Evidence and version/API notes live in
`specs/2026-10-18-phase-0-spikes/learnings.md`.
