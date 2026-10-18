# Phase 10: Packaging and evals. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 10 ("Packaging and evals"). Screens in scope (mock files in `docs/mock-source/`): all screens (final visual comparison against every file in `docs/mock-source/`).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-10-packaging-evals/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** a Windows installer anyone can run, with proof that it works.
**Requirements to cover:**
- PyInstaller (onedir) engine bundled into Electron resources; **no Python or Node needed on the user's machine**.
- electron-builder: **NSIS per-user installer and a portable zip**, unsigned. README explains the SmartScreen "More info > Run anyway" step with screenshots.
- First run: Persian UI, demo model available with no key, sample project that includes the example `read-framework-docs` skill.
- CI workflow: typecheck, lint, pytest, build installer artifact. Version 0.1.0.
- **Eval suite:** about 20 deterministic cases using the demo/fake model (jail escapes, risky commands, plan gate, verify gate, reflect loop budgets, approvals and rules, skills disclosure, question flow, crash and resume) plus a manual live-model checklist (one OpenAI-compatible model, one Anthropic). Output a short report file.
- `SECURITY.md` with honest limits (no sandbox, what the permission layer does and does not protect). Final `README.md` with screenshots from the real app, architecture diagram, how to add a model, skills, schedules.
- **Clean-machine test** (fresh Windows 10/11 VM or user): install, add a key, pick a folder, fix a failing-test task in under 5 minutes; every dangerous action shows an approval card; rejecting never crashes.
**Tests:** installer smoke test script, no orphan processes after quit, no secrets in the packaged app or logs.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
