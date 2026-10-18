# Phase 1: Walking skeleton. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 1 ("Walking skeleton"). Screens in scope (mock files in `docs/mock-source/`): `Home.dc.html` and `Main.dc.html` (shell and chat look only; sidebar in every file).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: re-read, do not rewrite
The spec for this phase already exists in `specs/2026-10-18-phase-1-walking-skeleton/`. Read it fully. If Phase 0 `learnings.md` contradicts it, list the contradictions and ask me before changing anything. Otherwise skip to Step B.

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** the thinnest end-to-end slice inside the real app shell. Use `specs/2026-10-18-phase-1-walking-skeleton/` (requirements R1..R10, plan steps 0..8, validation) as the contract.
**Highlights to get right:**
- Repo scaffold with the exact layout in `tech-stack.md` (`backend/ electron/ src/ build/ scripts/ skills/ docs/ .github/workflows/`), CI running all gates.
- Pydantic wire types generated to TypeScript (no hand copying). SSE with `seq`, `type`, `ts`, `Last-Event-ID` resume. Events persisted to `.harness/runs/<id>/events.jsonl`; replay reproduces UI state.
- `create_deep_agent` with a workspace-jailed filesystem backend, our own system prompt, SQLite checkpointer, demo model (and one real OpenAI-compatible model via env vars).
- App shell exactly like the mock: dark sidebar with icon nav (only **New task** works; Approvals, Customize, Schedule, Workspaces are visibly disabled placeholders), Settings gear pinned at the bottom, chat inside an inset surface with 24px rounded corners, Persian RTL by default, logical CSS only, tokens from `docs/design-tokens.md`.
- OpenUI `Renderer` with `Callout`, `Stack`, `KeyValue`; malformed output falls back to readable text.
- Electron: preload exposes only `{baseUrl, token, pickWorkspace()}`; no Node in the renderer; engine bound to 127.0.0.1; no orphan processes.
**Use Phase 0 `learnings.md` for every API detail.**

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
