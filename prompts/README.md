# Implementation prompts

Use these with any coding agent (Claude Code, Cursor, Codex, ...). Put the unzipped `codeharness` folder at the repo root first, so the agent can read `AGENTS.md`, `specs/`, `docs/design-tokens.md` and `docs/mock-source/`.

## Order
| Order | File | What |
|---|---|---|
| 1 | `00-kickoff.md` | paste once; the agent reads everything and lists risks |
| 2 | `phase-00-spikes.md` | de-risk OpenUI, PyInstaller sidecar, deepagents, Windows shell, reasoning stream |
| 3 | `phase-01-walking-skeleton.md` | spec already exists; implement the thin slice inside the real shell |
| 4 | `phase-02-models-workspace.md` | models, keys, presets, context auto-detection, workspace, Home |
| 5 | `phase-03-tools-permissions.md` | tools, permission layer, jail, undo, git, Workspace page |
| 6 | `phase-04-approvals-inbox.md` | interrupts, inbox, diff, rules |
| 7 | `phase-05-ask-user-question.md` | AskUserQuestion cards, `/grill` |
| 8 | `phase-06-planning-timeline.md` | plan, gates, Thinking panel, sub-agents |
| 9 | `phase-07-verify-context.md` | tests, verify gate, reflect loop, context ring |
| 10 | `phase-08-skills-customize.md` | skills, Customize hub, marketplace, MCP |
| 11 | `phase-09-render-ui-polish.md` | render_ui, all settings, states, themes |
| 12 | `phase-09b-schedule.md` | scheduler and Schedule UI |
| 13 | `phase-10-packaging-evals.md` | installer, CI, evals, README |
| any | `review-phase.md`, `spec-drift-fix.md`, `debug-prompt.md` | after each phase / when things disagree / when something breaks |

## How to run a phase
1. New session. Paste the phase file. The agent does **Step A** (writes the phase spec) and stops.
2. Read the three spec files. Reply `approved` or give changes.
3. The agent does **Step B** (implement, test, tick `validation.md`, write `learnings.md`).
4. New session: paste `review-phase.md` with the phase filled in. Fix findings, then move on.

## Tips
- Do phase 0 first; its `learnings.md` may change the constitution (the agent must ask you).
- Export a screenshot of each mock screen into `docs/mock/` if your agent can read images; the HTML in `docs/mock-source/` is the exact reference either way.
- Still open: the **Jev** and **Metis** URLs (phase 2 leaves those buttons disabled) and the web-search backend (phase 8 asks you).
- Keep sessions small: one phase, one goal. Commit after every plan step.
