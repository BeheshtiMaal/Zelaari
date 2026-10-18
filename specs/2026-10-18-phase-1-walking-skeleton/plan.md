# Phase 1: Walking Skeleton. Plan

Work top to bottom, commit after each step, do not skip validation.

## Step 0: Spike notes (Phase 0 outputs captured in `learnings.md`)
- Confirm installed `deepagents` version, the exact `create_deep_agent` kwargs (backend, skills, memory, middleware, checkpointer).
- Confirm a scripted fake chat model supports tool binding with `create_deep_agent`.
- Confirm OpenUI `Renderer` works inside the statically exported Next app under Electron (`file://` or custom protocol).

## Step 1: Scaffold the repo layout
- `backend/` (pyproject, ruff, mypy, pytest), root Next.js + Electron files, `.github/workflows`, `AGENTS.md`, `SECURITY.md` stub.

## Step 2: Wire types
- `backend/agent/events.py`: Pydantic models for all event types in the protocol, including `reasoning.delta` (Phase 1 subset implemented, rest stubbed).
- Generate TS types from JSON Schema into `src/lib/protocol.ts`. No hand copying.

## Step 3: Engine server
- `server/app.py` (auth dependency, locked CORS), `server/main.py` (free port, first stdout line `{"port":N}`).
- Routes: `/health`, `/runs`, `/runs/{id}/events`, `/runs/{id}/stop`.

## Step 4: Providers
- `providers/base.py` (provider record), `providers/demo.py` (scripted, tool-calling), `providers/openai_compat.py` (env-configured for now).

## Step 5: Agent
- `agent/factory.py`: `create_deep_agent(...)` with a jailed filesystem backend over the workspace, our system prompt, SQLite checkpointer.
- `agent/bridge.py`: consume `astream` output and emit typed events through an `EventBus`.
- `store/eventlog.py`: append-only jsonl writer. Cancellation via task cancel.

## Step 6: Electron main
- `electron/sidecar.ts`: spawn engine, read port, generate token, health-poll, kill process tree on `before-quit` and on crash.
- `electron/preload.ts`: `contextBridge` exposing `{baseUrl, token, pickWorkspace()}`. No Node in the renderer.

## Step 7: UI
- `src/store/run.ts` (zustand reducer fed by SSE via `fetch` streaming with auth header).
- `src/app/tasks/page.tsx`: input, streaming message, tool-call line.
- `src/genui/library.ts`: Zod-defined components `Callout`, `Stack`, `KeyValue`; generated prompt text used by the demo model's final message.
- `src/components/shell/`: sidebar (icons, disabled placeholders), inset rounded surface, dark theme tokens.
- `src/i18n/{fa,en}.ts`, logical CSS only.

## Step 8: Validate and update the specs
- Run every item in `validation.md`. Update `roadmap.md` (mark Phase 1 done, record learnings, adjust Phase 2).
