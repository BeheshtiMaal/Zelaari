# Phase 3: Tools and permission layer. Implementation prompt

> Paste this whole file into your coding agent from the repo root. One phase per session; start a fresh session for the next phase.

You are implementing **CodeHarness** phase 3 ("Tools and permission layer"). Screens in scope (mock files in `docs/mock-source/`): `Workspace.dc.html`, `Home.dc.html` (Worktree and branch), `Errors.dc.html` (timeout, jail block).

## Ground rules (apply to everything below)
- Work from the repo root. First read `AGENTS.md`, `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`, and `docs/design-tokens.md`.
- The **UI mock is the source of truth** for how screens look: read the listed files in `docs/mock-source/` (inline styles, exact Persian strings). Match layout, hierarchy, colors and copy; rebuild with React, Tailwind v4 and Radix. If a spec and the mock disagree, stop and ask me; do not silently pick one.
- Spec-driven: no product code for a phase before its spec is approved. Never edit the constitution (`mission`, `tech-stack`, `roadmap`) silently: propose the change, wait for approval, commit it with the code.
- Boundaries (jail, permissions, approvals) are enforced in code in the tool layer, never by prompting the model. Never log or store secrets. Never invent URLs, versions or API shapes: verify against installed packages or official docs, and record what you verified.
- Quality gates must pass before you say done: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` (plus the phase's own checks). Small modules, typed, tests next to behavior.
- Commit after each plan step with a clear message. Do not bundle unrelated changes.
- If something is ambiguous, ask me ONE short question at a time (offer 2 to 4 options with your recommendation) instead of guessing.

## Step A: write the phase spec, then STOP
Create `specs/<date>-phase-3-tools-permissions/` with `requirements.md`, `plan.md`, `validation.md` (use `specs/2026-10-18-phase-1-walking-skeleton/` as the format example: goal, in/out of scope, numbered requirements R1..Rn, ordered plan steps, checkbox validation split into Automated and Manual). Base them on the Phase brief below and on the constitution. Make every requirement testable. Then update the phase row in `specs/roadmap.md` if reality differs.
**Do not write product code in Step A.** End with a short summary and ask me to reply "approved" (or list changes).

## Step B: implement (only after I reply "approved")
Follow `plan.md` in order, one commit per step. Write the tests described in `validation.md` as you go (automated items must be real tests). When finished, run every automated check, walk through every manual check, tick the boxes in `validation.md`, write `learnings.md` in the phase folder (what you verified, deviations, surprises), and update `specs/roadmap.md`.

## Phase brief
**Goal:** the agent can read, edit, create files and run commands, all behind one permission authority, with undo.
**Requirements to cover:**
- **Tools:** deepagents filesystem tools, our `run_command` (PowerShell default, cmd fallback; per-command timeout default 120 s; output cap 200 lines with "show more"; process-tree kill) or the stock shell backend if Phase 0 proved it works on Windows.
- **Jail:** resolve real paths (symlink/junction aware), reject escapes; never run executables from the workspace by a UI click; scrub API keys from child-process environments.
- **Atomic writes** (temp file + rename) and **snapshots/undo** in `.harness/snapshots/` with a revert API.
- **Permission layer:** `PermissionMiddleware` is the single authority. Modes **Read-only / Ask (default) / Auto**; rules in `.harness/rules.json` per tool x path glob -> allow/ask/deny; defaults: reads allow, writes ask, commands ask, web ask, delete ask. `deny` returns a tool error the model can read; `ask` raises a LangGraph interrupt. **Always ask, even in Auto:** rules file and `.harness/` edits, web search queries (unless an explicit allow rule exists), high-risk commands.
- **Command risk classifier** with a table-driven test suite: recursive/forced delete, disk/format ops, registry edits, encoded PowerShell, pipe-to-shell downloads, `git push --force`, `git reset --hard`, `git clean -fd`, package install/uninstall, network tools, anything resolving outside the workspace. Include tricky cases (quoting, `&&` chains, aliases, case).
- **Temporary approval UI:** a minimal modal (approve/reject) so `ask` works end to end now; the full inbox is Phase 4.
- **Git bits:** branch chip reads `.git/HEAD`; switching runs `git switch` through the permission layer. **Worktree** checkbox (git repos only, git installed) runs the task in `git worktree` under `.harness/worktrees/<task-id>`; creating it is an approval; the user merges themselves.
- **Workspace page** (`Workspace.dc.html`): file tree (with a "system files" toggle for `.harness`), file viewer with agent-changed lines highlighted and a "waiting for approval" badge, the workspace's task list in the same screen; `GET /files`. There is **no separate Files page**.
- **Error states** from `Errors.dc.html`: command timeout, jail block (message says access is never allowed, even with approval).
**Security tests are mandatory:** junction/symlink escape, `..`, UNC, env scrubbing, rules-file protection in Auto mode, classifier table.

## Definition of done
- Every box in `validation.md` is ticked with evidence (test name or short note), quality gates are green, and the screens listed above match the mock.
- No TODOs left without an entry in `learnings.md`. No secrets in code, logs, events or fixtures.

## Report format (final message)
1. What was built (5 bullets max). 2. Evidence: command outputs summarized. 3. Deviations from spec or mock and why. 4. Open questions for me. 5. What the next phase needs from this one.
