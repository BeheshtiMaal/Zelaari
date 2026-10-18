# Phase 1: Walking Skeleton. Requirements

## Goal
Prove the whole architecture end to end with the thinnest slice: a desktop window where the user picks a folder and types a task; the Python engine
runs one **deepagents** run that can call `read_file`; the result streams back and renders through **OpenUI**. Uses the offline demo model, plus one real
OpenAI-compatible model via environment variables (the real model vault is Phase 2).

## In scope
- Electron shell that starts and stops the engine (dev: venv Python; prod path stubbed).
- Engine: FastAPI, bearer-token auth, `POST /runs`, `GET /runs/{id}/events` (SSE), `POST /runs/{id}/stop`, `/health`.
- `create_deep_agent` with a workspace-jailed filesystem backend, our own system prompt (replaces the default), SQLite checkpointer.
- Event bridge: map deepagents/LangGraph stream output to our typed events.
- Event log: `.harness/runs/<id>/events.jsonl`.
- UI (Next.js, static export loaded by Electron): Tasks page with input, streamed message, tool-call line, OpenUI `Renderer` using a first library
  (`Callout`, `Stack`, `KeyValue`). Fa/en dictionaries with RTL-safe CSS (only a handful of strings); **Persian is the default language on first launch**.
- App shell as in the mock: dark sidebar with icon nav (only **New task** works; Approvals, Customize, Schedule and Workspaces are disabled placeholders), Settings gear pinned at the bottom, chat in an inset rounded surface, dark theme.
- Demo model: scripted, offline, deterministic, supports tool calls.

## Out of scope
Writes, shell, permissions, approvals UI, questions, planning gates, skills, settings screens, installer.

## Functional requirements
- **R1** App window opens in under 3 s; input stays disabled until `/health` passes.
- **R2** Engine binds `127.0.0.1` only, on a random port, and rejects requests without the per-launch token (401).
- **R3** `POST /runs {task, workspace, model}` returns `{run_id}`. SSE events arrive in order with `seq`, `type`, `ts`, and support `Last-Event-ID` resume.
- **R4** Filesystem access is jailed: paths outside the workspace (including `..`, absolute, symlink or junction escapes) return a tool error the model can read.
- **R5** The final assistant message may contain OpenUI Lang. It renders progressively; if parsing fails the UI shows readable text, never a crash.
- **R6** Stop cancels the run within 1 s and emits `run.finished {status:"stopped"}`.
- **R7** Quitting (or killing) the app leaves no orphan engine process.
- **R8** Every event is persisted; replaying `events.jsonl` through the UI reducer reproduces the same state.
- **R9** The engine imports and runs without Electron (importable, testable on its own).
- **R10** No secrets in logs or events (test with a canary key).

## Non-functional
- CI green: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`.
- Folder layout matches `tech-stack.md` exactly.

## Decisions
- SSE over WebSocket: one-way stream, simple; commands use REST.
- Token reaches the UI through preload IPC, not through a URL.
- The demo model is a first-class provider (also used by tests and the evaluator's no-key first run).
