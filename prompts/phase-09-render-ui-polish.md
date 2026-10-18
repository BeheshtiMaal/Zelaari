# Phase 9: render_ui and polish. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 9 ("render_ui and polish"). Screens in scope (mock files in `docs/mock-source/`): `SettingsAppearance.dc.html`, `SettingsPermissions.dc.html`, `SettingsData.dc.html`, `SettingsAbout.dc.html`, `Empty.dc.html`, `Errors.dc.html`.

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-9-render-ui-polish/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** model-composed GenUI, finish every settings screen, states, themes, accessibility.
**Requirements to cover:**
- **`render_ui` tool:** the model writes OpenUI Lang restricted to our library (prompt generated from the library); parse and validate; on failure fall back to markdown and send the model a short error. The model can never render outside the library. Complete the library: `QuestionCard`, `PlanChecklist`, `ApprovalCard`, `DiffView`, `TerminalPanel`, `TestResults`, `FileTree`, `Callout`, `Stack`, `Tabs`, `Table`, `KeyValue`.
- **Settings screens, all functional:** Appearance and language (`SettingsAppearance.dc.html`), Permissions and safety (`SettingsPermissions.dc.html`: default mode, plan thresholds, deviation gate, locked always-ask list, rules table), Data and privacy (`SettingsData.dc.html`: paths, retention, web toggle, danger zone with confirmations), About (`SettingsAbout.dc.html`: version, MIT, honest "not a sandbox" note, open log folder).
- **Empty and error states** from `Empty.dc.html` and `Errors.dc.html`: every one reachable and tested (engine crash screen with "restart" and "view log").
- **Light theme** (derive tokens carefully), keyboard shortcuts, focus order, ARIA, reduced motion, RTL and LTR audit with logical properties only.
- i18n: every string in `fa` and `en` dictionaries; Persian digits in Persian UI.
**Tests:** OpenUI validation fallback, theme token coverage, a11y checks on dialogs, i18n completeness test (no missing keys).

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
