# Roadmap

Each phase is a feature spec in `specs/<date>-<phase>/`. Do not start phase N+1 until N's `validation.md` passes. Update this file between phases.
The UI mock (19 screens, Persian RTL, dark) is the visual source of truth; every screen is mapped to a phase below.

## Decisions log
| # | Question | Decision |
|---|---|---|
| D1 | Plan approval | Required only for bigger plans (>= 4 steps, or > 3 expected files, or a high-risk step). Follows the repo's permission model: modes Read-only / Ask / Auto and per-tool, per-folder allow/ask/deny rules |
| D2 | Test runners | Auto-detect pytest and npm test only. Custom test command setting. Else ask the user |
| D3 | Cost meter | Tokens only ("~" when estimated). No price fields. Hard limits independent of usage data |
| D4 | Packaging | NSIS installer and portable zip, unsigned |
| D5 | onboard-harness | Inspiration for design, folders and safety model; no code copied (it is AGPL) |
| D6 | Stack | Electron + Python sidecar; engine built on deepagents (LangGraph underneath) |
| D7 | Providers | Any OpenAI-compatible endpoint + Anthropic; the user supplies keys (DeepSeek, GLM, AvalAI, ...) |
| D8 | GenUI | OpenUI: AskUserQuestion, plan, approvals + diff, tests + terminal, plus polish |
| D9 | Default language | Persian (RTL) on first launch; English switch in Settings > Appearance |
| D10 | License | MIT |
| D11 | Web search | Ships ON; every query shows an approval card (approve / edit / reject). Stays `ask` even in Auto unless the user sets an explicit allow rule |
| D12 | Agent UI | deepagents has no UI; we build the activity timeline (thinking, plan, actions, sub-agents, context). Thinking shows only real provider reasoning |
| D13 | Chat box and shell | Composer with `+`, branch, permission mode, context ring (hover tooltip), model selector, send. Inset rounded chat surface next to the dark sidebar |
| D14 | Skills and Customize | Customize hub with sub-tabs Skills / Agents / Rules and permissions / Memory / Connectors (MCP). Skills tab: Installed / Marketplace / Mine; Marketplace = JSON catalog in a public Git repo (no hosted server). 5 bundled skills + 1 example project skill |
| D15 | Schedule | Tab + add dialog; runs only while the app is open; unattended default Read-only; approvals queue in the inbox |
| D16 | Approvals inbox | Two-pane, diff, allow-rule checkbox. Lists approvals only; questions are answered inline; several interrupts can be pending at once; waiting tasks get an amber dot |
| D17 | Add-model dialog | Dialog like Add schedule; no context, price or kind fields; preset buttons under Base URL |
| D18 | Settings | Seven sections: models, appearance, permissions, context, terminal and tests, data and privacy, about |
| D19 | States | Run screen (thinking, sub-agents, context notice, inline approval), empty states, error states |
| D20 | Mock is the source of truth | Where the specs disagreed with the mock, the specs were changed to match it (see "Audit log") |
| D21 | Worktree | Home screen has a Worktree checkbox: run the task in a `git worktree` (git repos only, approval to create) |

## Phases
| # | Phase | Outcome | Mock screens |
|---|---|---|---|
| 0 | **Spikes — complete** | Verified spikes: see `2026-10-18-phase-0-spikes/`. Both static-export protocols work; recommend `app://`; packaged Windows job/watchdog lifetime verified; deepagents 0.7.28 needs explicit todo middleware for the demo; stock Windows shell unsuitable; demo and reasoning-adapter behavior recorded; containment matrix verified. All 25 Python tests pass. | none |
| 1 | **Walking skeleton — complete** | Implemented Electron <-> engine <-> deepagents `read_file` runs with offline demo and a verified live OpenAI-compatible provider, generated wire types, durable SSE/replay and OpenUI in the Persian/English shell. All phase validation checks pass; see `2026-10-18-phase-1-walking-skeleton/validation.md`. | shell, sidebar |
| 2 | Models + workspace | Add/test models (dialog, presets, auto context detection), keys in safeStorage, workspace picker, demo model, token meter, minimal Settings > Appearance (language switch) | New task (home), Settings: models, Add model |
| 3 | Tools + permission layer | fs tools + `run_command`, workspace jail, atomic writes, snapshots/undo, rules.json, modes, risk classifier, branch chip (`git switch` via approval), Worktree option, Workspace page | Workspace (files + tasks) |
| 4 | Approvals inbox | interrupts, ApprovalCard + DiffView, approve/edit/reject, allow-rule checkbox, resume after restart, Rules tab | Approvals inbox |
| 5 | AskUserQuestion GenUI | `ask_user_question`, QuestionCard (single/multi/rank/free text), grill-me mode, amber dot for waiting tasks | Tasks (question moment) |
| 6 | Planning + activity timeline | `submit_plan`, PlanChecklist, plan gate (D1), deviation gate, Thinking panel, sub-agent rows, context-summarized notice | Run |
| 7 | Verify + self-correction + context ring | test detection (D2), TestResults + TerminalPanel, verify gate, reflect loop, budgets, context ring + breakdown + auto-compaction | Settings: context, terminal and tests |
| 8 | Skills + Customize hub | loader, `load_skill`, Skills tab (installed / marketplace / mine, toggles, detail, scan), install from folder/zip/git (approval), slash commands, 5 bundled skills + example project skill, Agents and Memory tabs, Connectors (MCP) tab | Customize: Skills (Connectors tab visible, inner screen not drawn) |
| 9 | `render_ui` + polish | model-composed GenUI, themes, fa/en, empty/error states, shortcuts, accessibility, remaining settings | Settings: appearance, permissions, data, about; Empty; Errors |
| 9b | Schedule | scheduler in engine (app-open only), Schedule tab, add dialog, templates, queued approvals, missed-run prompt | Schedule, Add schedule |
| 10 | Packaging + evals | PyInstaller + electron-builder (installer + zip, D4), CI, eval suite, README, SECURITY.md | none |

## Phase 0 handoff to Phase 1

Phase 0 is complete following technical validation and user approval of its constitution amendments. The
[learnings](2026-10-18-phase-0-spikes/learnings.md) and [validation](2026-10-18-phase-0-spikes/validation.md)
record the pinned APIs, examples, and evidence. Phase 1 must use explicit `TodoListMiddleware`, the custom `app://` protocol,
the packaged Windows job/watchdog lifetime pattern, and disabled inherited tracing. The demo model and captured stream/interrupt
shapes are available under `spikes/`. Preserve the containment candidate's documented race/alias limitations when designing the
product jail. Custom command execution remains Phase 3; live provider reasoning validation remains Phase 2. Phase order and scope
are unchanged. Phase 1 is complete, including the live-provider check using the user's external configuration file. Phase 2 has not started; it inherits the generated protocol, tested reducer and lifecycle, temporary environment/file provider configuration, and the documented jail limitations.

## Audit log (D20): the mock wins
The mock was left exactly as sketched. These spec statements were changed to match it:
- Skills: tab is called Marketplace (JSON catalog in a Git repo); 5 bundled skills plus `read-framework-docs` as an example project skill; `node-project` moved to backlog.
- Customize hub includes **Connectors (MCP)**; MCP moved from backlog into Phase 8.
- Permissions: delete defaults to `ask` while the mock shows a user-set `deny`; "deleting many files" folded into high-risk commands; the high-risk plan trigger is fixed
  (only step and file thresholds are settings).
- Schedule dialog has two controls: mode and access ceiling; the stricter one applies.
- Home screen has a **Worktree** checkbox (defined: run in a `git worktree`).
- Several interrupts can be pending at once, so Tasks can show a question and an approval together; inbox badge counts approvals only; amber dot marks waiting tasks.
- Thinking is reported per step (a step may have no reasoning even if another step has).
- Language switch lives in Settings, not on the first-run screen.
- Added guarantees the mock's error texts promise: atomic file writes, and no automatic replay of an in-flight command after a crash.

## Backlog
git-aware checkpoints, `node-project` skill, more test runners, macOS/Linux builds, code signing, auto-update, a hosted marketplace server.

## Open questions
1. The Jev base URL and the Metis OpenAI-compatible base URL (needed for the preset buttons). AvalAI is confirmed.
Nothing else blocks Phase 1.
