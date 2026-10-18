# Phase 7: Verify, self-correction, context ring. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 7 ("Verify, self-correction, context ring"). Screens in scope (mock files in `docs/mock-source/`): `Run.dc.html`, `Main.dc.html` (ring and popover), `SettingsContext.dc.html`, `SettingsTerminal.dc.html`, `Errors.dc.html` (exhausted, timeout).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-7-verify-context/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** the agent proves its work with tests, fixes its own failures in a bounded loop, and the user sees context usage.
**Requirements to cover:**
- **Test detection:** pytest (`pyproject.toml`, `pytest.ini`, `tests/`) and `npm test` (`package.json` scripts.test) only. Else the project setting (Settings > Terminal and tests, custom command); else ask via QuestionCard.
- **VerifyGateMiddleware:** if files changed and no verification command succeeded since the last change, the agent may not finish; inject "run the checks" and continue. Decision uses tool-call results, not the model's claim.
- **Reflect loop:** read failure output, decide fix vs re-plan. Limits: 3 fix attempts per step, 40 steps, 30 minutes per run (settings). On exhaustion stop and show the exhausted QuestionCard.
- **TestResults** and **TerminalPanel** components (xterm.js, read-only, red header and kill message on timeout).
- **Context ring** in the composer toolbar: small arc, no text; **hover tooltip** "38% · 48.8K / 128.0K context used" (Persian digits); click opens the breakdown popover (messages, tool results, system and tools, active skills, memory, red marker at the compaction threshold, "new chat with summary"). Uses the auto-detected window. Compaction starts at 60% (setting) via deepagents summarization/offload, emits `context.summarized`.
- **Settings > Context and compaction** and **Settings > Terminal and tests** exactly as in the mock (all controls functional).
- `usage.updated` events feed the token meter ("~" when estimated).
**Tests:** gate blocks early finish, bounded retries, exhaustion path, test detection matrix, compaction trigger, tooltip values.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
