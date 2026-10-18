# Phase 1 implementation evidence

Implementation approved by the user on 2026-10-18. Phase remains in progress until
every validation check passes. Constitution changes require separate approval.

## Step 0 — verified handoff

Read the entire Phase 0 learnings and installed deepagents 0.7.28 factory source,
the scripted model, Windows job launcher, containment candidate, OpenUI library,
progressive renderer and Electron protocol examples. No blocking contradiction
with the Phase 1 contract was found. Use explicit `TodoListMiddleware`, `app://`,
allowlisted environments with tracing disabled, and a watchdog holding a
kill-on-close job. Bind port zero once and serve the same socket.

OpenUI 1.0.1 uses `defineComponent`, `createLibrary`, `Renderer`, and
`library.prompt()`. The three-component prompt will be generated into a bundled
artifact, rather than hand-maintained in Python. SQLite checkpointing needs its
own package (not installed in the spike environment).

Phase 1 exposes file reads only. Backend operations and tool dispatch must reject
writes and commands independently of the model. The resolve-based jail has the
Phase 0 documented reparse-point race limitation; it is not an OS sandbox.

## Visual direction

Follow Home/Main exactly within Phase 1 scope: frame #1F2125, inset surface
#151618, cards #1E2024, composer #292B31, text #E8EAED, accent #0E7C86.
Bundled Vazirmatn, 240px right sidebar, 24px surface radius, 820px chat column,
Persian first launch and logical CSS. Later-phase controls are disabled.

## Implementation and installed API details

- Product dependencies are locked in root `package-lock.json` and `backend/uv.lock`.
  The Phase 0 core pins are preserved. SQLite persistence resolves to
  `langgraph-checkpoint-sqlite==3.1.2` with `aiosqlite==0.22.1`; verified installed
  `AsyncSqliteSaver.from_conn_string()` owns the connection for each asynchronous
  run. This is the asynchronous SQLite saver, rather than blocking `SqliteSaver`
  on FastAPI's event loop.
- OpenUI's installed peer dependency requires Zustand 4 (`4.5.7`), not Zustand 5.
  No forced peer resolution is used. Other new UI dependencies were verified via
  npm registry metadata before installation. Vazirmatn is bundled from
  `@fontsource/vazirmatn` and does not use Google Fonts at runtime.
- `backend/agent/events.py` is the wire authority. Pydantic JSON Schema generates
  `src/lib/protocol.ts` with `json-schema-to-typescript`. Reserved event names,
  including `reasoning.delta`, are typed but not emitted in this phase. The
  OpenUI library lives in `library.tsx` because its renderers contain JSX; its
  generated prompt is bundled as `backend/agent/genui_prompt.txt`.
- Actual `create_deep_agent` kwargs: `model`, `backend`, `checkpointer`,
  `system_prompt`, `middleware`. Middleware contains explicit
  `TodoListMiddleware`, a replacement `FilesystemMiddleware(tools=["read_file"])`
  and `ReadOnlyTools`. Filesystem automatic offloading is disabled for this thin
  read-only slice. The model is offered `read_file` and `write_todos`; forged
  writes, shell and delegation calls are rejected in dispatch. SQLite stores
  run threads; resuming a product conversation after restart is later work.

## Runtime findings covered by tests

- Filesystem middleware normalizes tool paths such as `README.md` to virtual
  `/README.md`. The jailed adapter interprets that prefix inside the workspace;
  it never treats it as an operating-system root. UNC/device paths, ambiguous
  Windows root/drive-relative paths, traversal, outside absolute paths, real
  symlinks/junctions and aliases into `.harness` remain rejected. Tests assert
  actual fixture contents through a real agent, not just event shapes.
- SSE uses FastAPI 0.146's installed `EventSourceResponse`/`ServerSentEvent` API.
  Event ids are the durable sequence numbers. The renderer fetches with a bearer
  header, handles fragmented UTF-8/SSE frames, reconnects after a truncated stream
  with `Last-Event-ID`, and reduces replayed and live events through one reducer.
- Stop publishes the terminal event before waiting for SQLite/HTTP cleanup.
  The terminal event bus rejects late events and duplicate finishes; shutdown
  awaits cancelled tasks. Waiting for cleanup before acknowledging Stop could
  exceed the one-second budget on Windows.
- Chromium in the installed Electron returns a Promise from `scrollIntoView()`
  (observed in `artifacts/desktop.json`). An implicitly returned browser value
  became an invalid React effect cleanup during streaming. The scroll effect
  explicitly returns nothing. The desktop test catches renderer exceptions.
- Electron's launcher PID can differ from the actual main-process PID under
  Playwright. Forced-termination tests use `app.evaluate(() => process.pid)` and
  assert engine liveness before killing that process. Killing the launcher alone
  is not a valid test of main-process lifetime. The watchdog retains the Phase 0
  kill-on-close job and EOF mechanism, supplemented by an open process handle to
  Electron main. It waits on that original handle, not a potentially reused PID.
- Development runs the same watchdog source with venv Python; the bundle uses
  `watchdog.exe` and `engine.exe`. Children start suspended and join the job before
  resuming. The native window is created before engine startup; input waits for
  authenticated health. Child environments are allowlisted and tracing disabled.
- PyInstaller data sources must be absolute when using `--specpath build/work`.
  The build helper resolves the prompt path, confines build output to this repo,
  and refuses to replace a running bundled engine. Optional MCP/timezone imports
  produce build warnings; neither is needed by this phase's verified demo path.

## Validation and evidence

Local automated checks have passed: ruff, strict mypy, 18 Python tests, TypeScript,
three UI unit tests, static export, Electron compilation and PyInstaller bundles.
Final desktop rerun includes Persian/English rendering, health gating, actual
fixture reads, malformed OpenUI fallback, persisted-log replay, loopback/auth,
and normal/forced cleanup for development and bundled lifecycles. Results are
recorded individually in `validation.md`; no CI service run is claimed because
this repository has no configured remote.

Screenshots under ignored `artifacts/` were visually inspected: home and run in
Persian and English, plus the malformed-output fallback. The native folder dialog
result is supplied deterministically in the desktop test; the actual preload IPC
and Electron dialog integration are exercised. The shell uses the mock's tokens,
240px sidebar, 24px inset surface and bundled font. Later-phase controls stay
disabled and no mock approval counts or sample workspace data are presented as
real state. Native window visibility was observed at roughly 0.25–0.42 seconds
of main-process uptime in an earlier passing desktop run.

## Live provider check — pending

The user's existing AvalAI environment key could fetch model metadata (HTTP 200,
including `gpt-4.1-mini`), but a tiny live chat request returned HTTP 429. No
successful live tool call is claimed. The user requested a file for an alternate
provider; created `%APPDATA%/CodeHarness/phase1-provider.env` with empty
`CODEHARNESS_BASE_URL`, `CODEHARNESS_MODEL`, `CODEHARNESS_API_KEY` fields. Both
Electron and `scripts/check_live.py` read it. It is outside the workspace and
never committed or printed. Awaiting the user's “ready” before using it.

Phase 1 cannot be marked complete until that live validation passes. Phase 2
should replace this temporary environment/file setup with provider records and
safeStorage, preserve the protocol/reducer and lifecycle tests, and add the
Settings language switch. Jev/Metis presets and the web backend remain unchanged
future decisions; nothing was guessed or implemented for those phases.
