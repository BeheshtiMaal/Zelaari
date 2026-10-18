# Phase 4: Approvals inbox. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 4 ("Approvals inbox"). Screens in scope (mock files in `docs/mock-source/`): `Inbox.dc.html`, `Main.dc.html` and `Run.dc.html` (inline approval card), `Skills.dc.html` (only the Customize hub chrome for the Rules tab).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-4-approvals-inbox/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** every sensitive action becomes an approval the human can approve, edit, or reject, and runs survive restarts.
**Requirements to cover:**
- LangGraph interrupts with `SqliteSaver`; **resume after app restart**; multiple interrupts can be pending at once (parallel tool calls); the run resumes when all are answered. An in-flight command is **never replayed automatically** after a crash: mark it interrupted, show it, tell the model.
- **ApprovalCard** and **DiffView** (unified diff with line numbers, add/remove tints) as OpenUI library components; inline in the run (see the amber card in `Main.dc.html` and `Run.dc.html`) and in the inbox.
- **Inbox page** (`Inbox.dc.html`): left list (type icon, title, source task or schedule, risk chip, in-plan chip, command preview, time) and detail pane (agent's reason, diff, snapshot/undo note, "don't ask again for `src/**`" checkbox that writes an allow rule, rejection reason textarea, Approve / Edit input / Reject with reason, Enter and Esc shortcuts). Tabs Pending / Approved / Rejected / All; recent decisions listed dimmed.
- **Decisions:** approve; edit input then approve; reject with reason (returned to the model as a tool result, run continues). `GET /approvals`, `POST /runs/{id}/interrupts/{iid}`.
- Sidebar **badge** = pending approvals across tasks and schedules; an **amber dot** marks any task waiting on you (approval or question).
- **Customize > Rules** tab (rules grid editor for `.harness/rules.json`); changing rules always asks, even in Auto.
- Replace Phase 3's temporary modal.
**Tests:** approve/edit/reject paths, resume after restart (kill the engine mid-interrupt), concurrent interrupts, allow-rule creation, badge counts.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
