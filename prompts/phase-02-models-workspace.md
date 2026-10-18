# Phase 2: Models and workspace. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 2 ("Models and workspace"). Screens in scope (mock files in `docs/mock-source/`): `Home.dc.html`, `Settings.dc.html`, `SettingsAddModel.dc.html`, `SettingsAppearance.dc.html` (language switch only), `Empty.dc.html` (no workspace, no model), `Errors.dc.html` (model errors).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-2-models-workspace/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** a user can add models with their own keys, pick a workspace, and start a task from the Home screen.
**Requirements to cover:**
- **Settings shell** (sidebar of 7 sections; only *Models and keys* and a minimal *Appearance* with the **language switch** Persian/English are functional now; the rest are placeholders).
- **Models page** (`Settings.dc.html`): provider cards (name, base URL, model, auto-detected context, masked key, test result, default chip, Test and Edit buttons) plus the demo model (offline, no key).
- **Add-model dialog** (`SettingsAddModel.dc.html`): dimmed backdrop, rounded dialog; fields name, Base URL, API key, model name; **preset buttons under the Base URL** that fill it: OpenAI `https://api.openai.com/v1`, Anthropic `https://api.anthropic.com`, AvalAI `https://api.avalai.ir/v1`, and **Jev** and **Metis** buttons that stay disabled with a tooltip "URL pending" until I give you their URLs (never invent them). Presets live in `backend/providers/presets.json`. No price, context or kind fields.
- **Provider kind is inferred** (Anthropic preset or `api.anthropic.com` means native Anthropic; everything else OpenAI-compatible).
- **Keys:** Electron `safeStorage` (DPAPI); engine receives keys in memory only; never written to the workspace, logs or events; add a canary-secret test.
- **Test connection:** makes a tiny tool-call probe; reject models without tool calling with the red/amber message from `Errors.dc.html`; map 401 and 429 to the messages in the mock (429 uses automatic backoff, max 3 tries).
- **Context window auto-detection**, in order: `/models` metadata, built-in model-name table (`backend/providers/context_table.json`), parse the limit from a context-length error, else conservative 32K shown with "~".
- **Reasoning:** capture reasoning text per provider if available and emit `reasoning.delta`; document per provider whether it works.
- **Token meter:** tokens used (provider usage if reported, else estimate marked "~"); no cost display.
- **Workspace picker:** native folder dialog; refuse drive roots and the user's home folder; remember recent workspaces; Workspaces list in the sidebar (name, expandable tasks list).
- **Home screen** (`Home.dc.html`): greeting, quick-start chips, large composer with placeholder, second bar (workspace dropdown, branch chip showing the current branch if a git repo, permission mode dropdown). The **Worktree checkbox** is rendered disabled with a tooltip until Phase 3. Context ring is a static placeholder (real in Phase 7).
- **Empty states** from `Empty.dc.html`: no workspace and no model (with "Use demo model").
**Out of scope:** permissions UI, approvals, planning, skills.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
