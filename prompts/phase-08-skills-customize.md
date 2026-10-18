# Phase 8: Skills, Customize hub, Connectors. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 8 ("Skills, Customize hub, Connectors"). Screens in scope (mock files in `docs/mock-source/`): `Skills.dc.html` (and the Customize hub chrome), `Home.dc.html` and `Main.dc.html` (skills chip, `/` picker).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-8-skills-customize/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** add capabilities as skill folders and manage them in the Customize hub; connect MCP servers.
**Requirements to cover:**
- **Skill format:** folder with `SKILL.md` (frontmatter `name`, `description`, optional `command`), optional `scripts/`, `references/`. Locations: workspace `.harness/skills/`, user `%APPDATA%/CodeHarness/skills/`, bundled `skills/`. Progressive disclosure: only name and description go into the prompt; body loads on demand (`load_skill`). Skill scripts run through the normal command tool and permission layer.
- **Install** from folder, ZIP or Git URL: always an approval; **security scan** before first use (list scripts, flag risky patterns); per-workspace enable switch.
- **Bundled (5):** `grill-me` (`/grill`), `feature-spec` (`/spec`, runs the SDD workflow: constitution, feature spec, implement, validate), `fix-failing-tests` (`/fix`), `python-project`, `web-search` (`/search`). Plus `read-framework-docs` as an example project-level skill shipped in the sample project (off by default). Write real, good SKILL.md content for each. **web-search** ships enabled; every query shows an approval card (approve / edit query / reject), even in Auto. Use a pluggable search provider; ask me which backend to use before choosing one (a keyless default is acceptable if I agree).
- **Customize hub** with sub-tabs Skills, Agents (custom sub-agents as `.harness/agents/<n>.md`), Rules and permissions (from Phase 4), Memory (edit `.harness/memory.md`), Connectors (MCP).
- **Skills tab** exactly like `Skills.dc.html`: Installed / Marketplace / Mine tabs, search, category chips, cards (name, source badge, description, slash command, "requires approval" chip, security-scan status, token cost, switch), detail panel with `SKILL.md`, import and create buttons. **Marketplace** = a JSON catalog in a public Git repo (configurable URL), no hosted server, no accounts; installing goes through the same approval and scan.
- **Connectors (MCP):** cards per server (name, command or URL, status, tools); tools loaded via an MCP adapter, namespaced `server__tool`, every call through `PermissionMiddleware` (default ask); adding a stdio server is a command-execution approval; config in `.harness/mcp.json`; secrets never written to the workspace. The mock shows the tab only: design the inner screen to match the Skills tab style and show it to me before building.
- Slash commands from skills appear in the composer `/` picker; skills chip in the composer shows active skills.
**Tests:** loader and frontmatter validation, progressive disclosure (prompt contains only name and description), install and scan, enable per workspace, web-search approval always asked, MCP permission path.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
