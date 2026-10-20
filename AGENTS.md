# AGENTS.md

CodeHarness is built **spec-first** (spec-driven development). Before writing code:

1. Read the constitution: `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md`, `specs/challenge-traceability.md`.
2. Work on ONE roadmap phase at a time. Its spec lives in `specs/<date>-<phase>/` (`requirements.md`, `plan.md`, `validation.md`).
3. Implement the plan in order. A phase is done only when every check in `validation.md` passes.
4. If reality contradicts a spec, STOP, update the spec (and roadmap) first, then code.
5. Never edit the constitution silently. Propose the change, get approval, commit it together with the code.

Reference material: `docs/mock-source/*.dc.html` (UI mock, source of truth for screens), `docs/design-tokens.md`, and `prompts/` (one implementation prompt per phase, plus review, drift and debug prompts).

Conventions
- Engine (Python): typed, small modules, `ruff` + `mypy --strict` + `pytest`. Every tool and every permission path has a test.
- UI (TypeScript): strict, logical CSS properties only (RTL-safe), no business logic in components.
- No secrets in logs, events, or the workspace.
- Reference design: https://github.com/TahaHosseinpour/onboard-harness (AGPL-3.0). We take ideas and structure, never copy code. This project is MIT.
- also read `prompts/00-kickoff.md`

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
