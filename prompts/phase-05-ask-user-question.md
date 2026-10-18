# Phase 5: AskUserQuestion GenUI. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 5 ("AskUserQuestion GenUI"). Screens in scope (mock files in `docs/mock-source/`): `Main.dc.html` (question card), `Errors.dc.html` (exhausted card), `Home.dc.html` (composer `/` and `@` hints).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-5-ask-user-question/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** the agent can stop and ask structured questions rendered as interactive cards; includes grill-me.
**Requirements to cover:**
- Tool `ask_user_question`: 1 to 3 questions; each has a short header chip, text, 2 to 4 options each with a description, `type: single | multi | rank`, and a free-text "Other" always available. Returns structured answers; dismiss returns "declined". The tool description tells the model to ask only when the answer cannot be found by reading the project.
- **QuestionCard** (OpenUI component) exactly like the docked card in `Main.dc.html`: header chip ("approach"), "question 1 of N", options with radio/checkbox/rank handles, "Other" input, hint "1 to 3 to choose, Enter to send", send button. Keyboard: 1-4, Enter, Esc. Accessible (focus, ARIA, RTL).
- Used by: clarify step, test-command prompt (Phase 7), **fix attempts exhausted** card (see `Errors.dc.html`: retry with a hint / change approach / stop and report).
- **`/grill` mode** (built-in for now; Phase 8 repackages it as the `grill-me` skill): interviews one batch at a time until the task is fully specified, then proceeds.
- Questions are answered inline in their run; waiting tasks show the amber dot; a question and an approval can be pending together (right panel counts what waits in the current task, as in `Main.dc.html`).
- The `/` picker in the composer lists commands (start with `/grill`).
**Tests:** schema validation, each question type, declined path, keyboard, resume after restart while a question is pending.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
