# Phase 0: Spikes. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 0 ("Spikes"). Screens in scope (mock files in `docs/mock-source/`): none (technical spikes). Look at `Home.dc.html` only to see what the final chat surface will need to render.

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-0-spikes/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** de-risk the stack with throwaway experiments before any product code. Output is knowledge, not features.
**Do (under `spikes/`, throwaway):**
1. **OpenUI in Electron:** Next.js 16 static export loaded by Electron (try `file://` and a custom `app://` protocol). Define a tiny Zod component library (`Callout`, `Stack`, `KeyValue`) with `@openuidev/react-lang` / `@openuidev/react-ui`, render a progressively streamed OpenUI Lang string, and test malformed input fallback. Record the exact package versions and the prompt-generation API.
2. **Engine as a sidecar:** FastAPI app packaged with PyInstaller (onedir) and launched by Electron. Prove: random free port printed on the first stdout line, per-launch bearer token, health check, kill of the whole process tree on quit and on a force-killed Electron.
3. **deepagents:** pin the version. Confirm real signatures of `create_deep_agent` (backend, skills, memory, subagents, middleware, checkpointer, interrupt handling), how to fully replace the system prompt, how `write_todos` and sub-agent (`task`) activity appear in the stream, and the interrupt/resume decision format. Test the stock local shell backend on Windows (PowerShell, cmd) including timeout and process-tree kill.
4. **Demo model:** a scripted chat model that streams text, emits tool calls, and works with `create_deep_agent` tool binding.
5. **Reasoning stream:** check whether DeepSeek-style `reasoning_content` and Anthropic thinking blocks reach us through `langchain-openai` / `langchain-anthropic`; record how to read them (this feeds the Thinking panel).
6. **Jail on Windows:** test symlink and junction escapes, `..`, drive-relative and UNC paths against a resolve-and-contain check.
**Output:** `specs/phase-0-spikes/learnings.md` with: pinned versions, verified API shapes, working code snippets, failures and workarounds, and a list of **spec statements that must change** (propose edits to `tech-stack.md`; do not apply them silently). Keep spike code out of the product folders.
**Not in scope:** any product UI, settings, or persistence.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
