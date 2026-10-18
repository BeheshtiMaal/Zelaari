# Phase 9b: Schedule. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 9b ("Schedule"). Screens in scope (mock files in `docs/mock-source/`): `Schedule.dc.html`, `ScheduleAdd.dc.html`, `Empty.dc.html` (no schedules).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-9b-schedule/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** scheduled tasks that respect human-in-the-loop even when nobody is watching.
**Requirements to cover:**
- Scheduler in the engine (e.g. APScheduler); schedules stored in the app database (`%APPDATA%/CodeHarness/app.sqlite`), not in the workspace. **Runs only while the app is open**; missed runs are offered as "run now" at next launch. No background service.
- **Schedule page** (`Schedule.dc.html`): active list rows (title, workspace and recurrence, mode chip, last result or "N approvals queued", on/off switch, more menu) and the popular-templates grid (nightly tests, daily git review, weekly dependency check, test coverage, TODO cleanup, weekly summary).
- **Add dialog** (`ScheduleAdd.dc.html`): name, prompt box (with improve-text sparkle and **mode** chip: Read-only / Ask / Auto), workspace, **access ceiling** chip (read-only and report, or full access shown in red with the warning), Repeat, Time, Validity. **The stricter of mode and access ceiling applies.** Unattended default is Read-only plus report.
- Each run is a normal run with its own `events.jsonl`; results appear as a task under the workspace; approvals queue in the Approvals inbox and the run pauses until the user returns; full access never bypasses the always-ask list.
- Empty state for no schedules.
**Tests:** recurrence math (weekly Friday 09:00 etc.), missed-run handling, mode x ceiling matrix, queued approval pauses the run, schedule survives restart.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
