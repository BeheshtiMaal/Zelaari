# Phase 6: Planning and activity timeline. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 6 ("Planning and activity timeline"). Screens in scope (mock files in `docs/mock-source/`): `Run.dc.html`, `Main.dc.html`.

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-6-planning-timeline/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** analyze first, plan, follow the plan visibly, and show everything the agent does as a live timeline.
**Requirements to cover:**
- Tool `submit_plan` (ordered steps; each has title, expected file globs, optional verify command); progress via deepagents `write_todos`; engine emits `plan.created` / `plan.step.updated`.
- **Plan gate:** approval required for 4 or more steps, or more than 3 expected files, or any high-risk step; thresholds (steps, files) are settings; the high-risk trigger is fixed; Auto mode skips the gate. **Deviation gate** (default on, Ask and Auto): files outside declared globs, more than 2 added steps, or a dropped step raises an approval showing the plan diff.
- **PlanChecklist** component and the right-panel plan (done / in progress / pending).
- **Run screen** (`Run.dc.html`): header with status chip, elapsed time and token usage, Stop; finished steps collapsed to one line (duration, counts, thinking note); active step expanded with the **Thinking panel** (`reasoning.delta`, streaming caret, auto-collapse when the step ends, per-step "no reasoning sent" text, only real provider reasoning); **sub-agent blocks** (reviewer and researcher, both read-only; delegated task, mini timeline, result, status and duration, collapsible; several can run at once via `subagent.started/finished`); the "context summarized" notice (`context.summarized`); inline approval card.
- Right panel: plan, sub-agents, context bar, limits (steps, fix tries), "N waiting for you".
- **Composer mid-run:** messages steer the agent; send becomes Stop.
- System prompt rules: analyze before editing, small steps, follow the plan, report deviations.
**Tests:** plan gate thresholds, deviation gate, event ordering with sub-agents, collapse/expand state, Stop within 1 s.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
