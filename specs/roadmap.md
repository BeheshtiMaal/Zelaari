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
| D22 | Run "steps" counter | `گام‌ها ۷ از ۴۰` counts agent iterations, not plan steps: the mock shows it at plan step 3 of 4, so it cannot be plan progress |
| D23 | Test detection order | Custom command → pytest → npm. A repo with both runners gets pytest; Settings shows what was detected and a custom command overrides both |
| D24 | Breakdown numbers | Per-category rows are estimates (`~`); the total uses provider usage when reported, so the ring is exact and the rows are honest |
| D25 | Unknown test command | The agent asks through `ask_user_question`; a middleware cannot raise the Phase 5 barrier without duplicating it, so the gate verifies the call happened and adopts the answer |
| D26 | Terminal renderer | xterm.js (`@xterm/xterm` 6.0.0 + `@xterm/addon-fit` 0.11.0), output-only. The `<pre>` fallback was not needed; the install worked offline |
| D27 | The generated schema is the validator's contract | One library (`library.tsx`) produces both the model's prompt and the JSON schema the Python validator reads. No component list is maintained in Python, so React and the validator cannot disagree |
| D28 | `render_ui` is read-only, so it never asks | It changes no file, no rule and no permission. A tool that asked on every render would train the person to click approve without reading |
| D29 | Light theme is a palette, not a second tree | Every colour is a token and every size is a type step, so the same components render in both themes. The sweep was a precondition, not a follow-up |
| D30 | The font preference scales type tokens, not `zoom` | xterm measures its own cell size; `zoom` breaks it. `--fs-scale` multiplies every `--fs-*` step instead |
| D31 | The crash screen keeps the app alive | A sidecar exit used to destroy the windows. It now reports `engine-status` and offers `restart-engine`, which is the only way "restart" can exist |
| D32 | Destructive rows use two confirmations | A dialog that names the loss, then an explicit checkbox — not an inbox approval. They are the person's own action on their own app data, and an inbox approval would mean approving themselves |
| D33 | A fresh install is dark | The mock is dark and the product is Persian-first; the OS preference is one click away under `مثل سیستم`. Following the OS by default would make the first screen depend on a machine setting nobody chose here |
| D34 | Schedules live in `catalog.json`, not a new `app.sqlite` | The tech stack names an SQLite file this product has never had: models, settings, tasks and approvals all live in one atomically-written JSON catalog that the Data screen already reports. A second store means two things to back up, clear and migrate. **Proposed, awaiting approval — it changes a constitution line** |
| D35 | An asyncio ticker, not APScheduler | A library with its own thread pool and its own persistence, running work that must stop when the process stops, buys nothing. ~40 lines plus a pure `next_run_after` cannot outlive the app and is testable with a fixed clock |
| D36 | A missed run is a row, not a run | The app cannot know whether the machine slept, the person was away or the workspace moved. Starting unattended work the moment the window opens would queue approvals before anyone has looked at anything |
| D37 | `min(mode, ceiling)` is applied once, in the engine, before `RunRequest` exists | No later layer has to remember the ceiling, and a schedule cannot widen its own permission by being edited while a run is queued |
| D38 | `schedule_id` on the request and on the task record | That one link makes "N approvals queued", "which schedule made this" and the row's last result answerable from what is already persisted, with no second ledger |
| D39 | Creating a schedule needs no inbox approval | It is the person's own action on their own app (the D32 reasoning). Full access is the exception that stays visible: a red warning and an explicit choice |
| D40 | Every due schedule starts its own run; no global cap | A run paused on an approval must not hold the queue, and the inbox already holds several pending approvals at once |
| D41 | A paused group sits under the active one | The mock draws only `فعال (۲)`; a switched-off schedule has to appear somewhere. An extension, not a contradiction |
| D42 | The six-cell table exists twice and both are tested | The dialog answers before a round trip, the engine answers when a run starts. The engine's answer is authoritative; the dialog's is a display of it |
| D43 | The row shows the effective mode, not the chosen one | A schedule stored as `ask` under a `report` ceiling runs read-only. A chip that says "with approval" would describe a run that never happens |
| D44 | A centred dialog flips its `transform` in RTL | `transform` has no logical form, so `inset-inline-start: 50%` plus `translate(-50%, -50%)` parks a dialog half a width off-screen in Persian. One `[dir="rtl"]` rule now covers all four dialogs, and a test fails if a new one forgets it |

## Phases
| # | Phase | Outcome | Mock screens |
|---|---|---|---|
| 0 | **Spikes — complete** | Verified spikes: see `2026-10-18-phase-0-spikes/`. Both static-export protocols work; recommend `app://`; packaged Windows job/watchdog lifetime verified; deepagents 0.7.28 needs explicit todo middleware for the demo; stock Windows shell unsuitable; demo and reasoning-adapter behavior recorded; containment matrix verified. All 25 Python tests pass. | none |
| 1 | **Walking skeleton — complete** | Implemented Electron <-> engine <-> deepagents `read_file` runs with offline demo and a verified live OpenAI-compatible provider, generated wire types, durable SSE/replay and OpenUI in the Persian/English shell. All phase validation checks pass; see `2026-10-18-phase-1-walking-skeleton/validation.md`. | shell, sidebar |
| 2 | **Models + workspace - complete** | Implemented model settings/probes, safeStorage credentials, auto context detection, provider reasoning/usage, Home, workspace recents/task replay and remembered language. Local Windows checks, live OpenAI and Claude Home runs through the supplied compatible endpoint, and a live native Anthropic Messages adapter run pass; see `2026-10-19-phase-2-models-workspace/validation.md`. | New task (home), Settings: models, Add model |
| 3 | **Tools + permission layer - complete** | Jailed filesystem tools, atomic writes, snapshots and UI undo, process-tree command timeout, rules and modes, risk classifier, temporary approvals, approved branch switching, isolated worktrees, Workspace viewer and timeout/jail cards. Windows Electron evidence and quality gates recorded in 2026-10-19-phase-3-tools-permissions/validation.md. | Workspace (files + tasks) |
| 4 | **Approvals inbox - complete** | Durable SQLite approval barriers, approve/edit/reject, unified diffs, linked allow-rule review, Rules grid, global counts and waiting dots, restart recovery and no replay of uncertain effects. Offline demo and Windows Electron evidence recorded in `2026-10-19-phase-4-approvals-inbox/validation.md`. | Approvals inbox |
| 5 | **AskUserQuestion GenUI - complete** | Durable structured questions with single/multi/rank/Other, declined results, shared docked QuestionCard, mixed question/approval barriers and restart recovery, current-task waiting summary, built-in `/grill` interview and composer picker, exhausted-attempts integration contract. Windows Electron and offline evidence recorded in `2026-10-19-phase-5-ask-user-question/validation.md`. | Tasks (question moment), Errors (exhausted card), Home (command picker) |
| 6 | **Planning + activity timeline - complete** | Structured plans, reviewed initial/deviation gates and workspace settings, stable todo progress, trusted PlanChecklist, scoped reasoning and concurrent read-only delegates, actual summarization notices, truthful telemetry, durable steering and cancellation/recovery. Offline engine and Windows Electron evidence is recorded in `2026-10-19-phase-6-planning-timeline/validation.md` and `learnings.md`. | Run |
| 7 | **Verify + self-correction + context ring - complete** | Test detection (D2), the verify gate and unknown-command question, bounded self-correction with the exhausted card, real step/time/fix budgets, TestResults + read-only xterm terminal with the timeout variant, context ring + breakdown + auto-compaction with summary handoff, and both settings screens behind the configuration approval. Offline engine and Windows Electron evidence is recorded in `2026-10-24-phase-7-verify-context/validation.md` and `learnings.md`. | Settings: context, terminal and tests |
| 8 | **Skills + Customize hub - complete** | Skills as folders (bundled / user / project) with a bounded frontmatter parser, a pre-use scan, per-workspace switches, progressive disclosure (`load_skill`), install from folder/ZIP/Git through the protected approval, a JSON marketplace catalog, slash commands, the five bundled skills plus the sample project skill, `web_search` that always asks, MCP connectors with `server__tool` names through the permission gate, and the Agents / Memory / Rules / Connectors tabs. Offline engine and Windows Electron evidence is recorded in `2026-10-25-phase-8-skills-customize/validation.md` and `learnings.md`. | Customize: Skills, Connectors (inner screens now drawn) |
| 9 | **`render_ui` + polish - complete** | One OpenUI library generating both the model's prompt and the validator's JSON schema, a bounded parser and a schema-driven validator, `render_ui` as a read-only tool that never asks, the twelve components drawn in the timeline with the failure note kept, seven settings sections (appearance and language, permissions and safety with the engine's five locked rows, data and privacy with a two-confirmation danger zone, about), two palettes from one token set with an 18-step type scale, six empty states, a crash card with `restart-engine`, one keyboard table, a skip link, one focus ring, and fa/en parity enforced by test. Offline engine and Windows Electron evidence is recorded in `2026-10-25-phase-9-render-ui-polish/validation.md` and `learnings.md`. | Settings: appearance, permissions, data, about; Empty; Errors |
| 9b | **Schedule - complete** | An engine-side asyncio ticker that runs only while the app is open, schedules stored in the app-data catalog, the six-cell mode × ceiling table enforced once at run creation, a missed occurrence offered as a row ("run now" or "skip") instead of started, `schedule_id` linking every run and approval back to its schedule, the Schedule screen with active/paused groups and six templates, an add/edit dialog where the stricter of two permissions wins, and four walkthrough-found defects fixed (including every dialog being half a width off-screen in Persian). Offline engine and Windows Electron evidence is recorded in `2026-10-25-phase-9b-schedule/validation.md` and `learnings.md`. | Schedule, Add schedule |
| 10 | Packaging + evals | PyInstaller + electron-builder (installer + zip, D4), CI, eval suite, README, SECURITY.md | none |

## Phase 0 handoff to Phase 1

Phase 0 is complete following technical validation and user approval of its constitution amendments. The
[learnings](2026-10-18-phase-0-spikes/learnings.md) and [validation](2026-10-18-phase-0-spikes/validation.md)
record the pinned APIs, examples, and evidence. Phase 1 must use explicit `TodoListMiddleware`, the custom `app://` protocol,
the packaged Windows job/watchdog lifetime pattern, and disabled inherited tracing. The demo model and captured stream/interrupt
shapes are available under `spikes/`. Preserve the containment candidate's documented race/alias limitations when designing the
product jail. Custom command execution remains Phase 3; live provider reasoning validation remains Phase 2. Phase order and scope
are unchanged. Phase 1 is complete, including the live-provider check using the user's external configuration file. Phase 2 is complete; safeStorage and stable provider IDs replace the temporary desktop environment/file provider configuration. Phase 3 inherits generated protocol types, tested replay/lifecycle, native and engine workspace validation, workspace/task history, current branch metadata and recorded modes. Preserve the documented jail limitations. Worktree and branch switching remain Phase 3; the context ring remains Phase 7. Provider inference is unchanged: custom gateways use the OpenAI-compatible adapter. Native Anthropic SDK live evidence uses an explicit diagnostic override against the supplied gateway, separately from the live Home checks.

## Phase 3 handoff to Phase 4

Phase 3 is complete; all validation checks pass with Windows Electron evidence recorded in
`2026-10-19-phase-3-tools-permissions/validation.md`. Phase 4 inherits in-memory temporary approvals and adds
the durable inbox, edit/reject flows, allow-rule checkbox and Rules UI. The synthetic timeout retry and English
approval reasons remain documented limitations for Phase 4 to consider. No later phase is renamed or reordered.

## Phase 4 handoff to Phase 5

Phase 4 is complete; validation and verified package/recovery behavior are recorded in
`2026-10-19-phase-4-approvals-inbox/validation.md` and `learnings.md`. Phase 5 inherits durable
approval records, a pre-tool graph barrier with independently keyed decisions, edited-input previews
bound to current file contents, command/effect journals, replayable events, shared OpenUI approval
components and a Rules editor. Extend the barrier for question answers while preserving tool-call
identity and the rule that execution waits for all required answers. Questions stay inline and never
increase the approvals badge; `TaskRecord.waiting_on` already reserves the `question` kind. Preserve
credential rehydration and original provider identity checks on recovery, and never redispatch an
incomplete effect intent. User-initiated Rules, branch, worktree and retry actions have durable
configuration approvals without a model thread. Schedule production remains Phase 9b; plan metadata
remains Phase 6. Existing workspace-jail race/alias limitations remain documented; this is not an OS sandbox.

## Phase 5 handoff to Phase 6

Phase 5 is complete; validation, installed API contracts and scope choices are recorded in
`2026-10-19-phase-5-ask-user-question/validation.md` and `learnings.md`. Phase 6 inherits a durable
mixed human barrier with independently keyed approvals and question answers, original graph interrupt
identity, replayable question events and shared trusted OpenUI QuestionCard controls. Preserve the rule
that every required request in a model turn is resolved before any sibling tool executes. Questions stay
inline, current-task counts include question batches and approvals, the global badge counts approvals
only, and task dots cover both. Extend these contracts for planning/activity rather than introducing
another interrupt inside the tools node. Preserve provider/vault recovery, explicit Stop cancellation,
redaction before checkpointing and no automatic replay of uncertain effects. Built-in `/grill` persists
interview state and requires an answered batch plus a structured readiness summary before normal
implementation permissions can apply. Phase 7 consumes the question tool for unknown test commands and
the typed exhausted-attempts constructor/results for retry with hint, change approach and stop/report;
automatic fix budgets and verification gates remain Phase 7. Phase 8 repackages interview instructions
as the grill-me skill and extends the command picker. Context attachments, scheduler and packaging
delivery retain their assigned scope. Existing workspace-jail limitations remain; this is not an OS sandbox.

## Phase 6 handoff to Phase 7

Phase 6 is complete; validation and installed-runtime contracts are recorded in
`2026-10-19-phase-6-planning-timeline/validation.md` and `learnings.md`. Phase 7 inherits
engine-owned plan/revision/step identities, conservative concrete-file counting,
workspace planning settings behind protected configuration review, and the existing
mixed human barrier. Plan adoption never authorizes an unclassified sibling effect or
bypasses ordinary tool permissions, workspace containment or the effect journal.

Parent turns and read-only reviewer/researcher invocations have durable scoped activity,
provider/model attribution, real reasoning, replayable progress and honest interrupted
states. Completed delegate results survive recovery; uncertain effects are never replayed.
Steering is ordered and idempotent, enters the original parent thread only at a checkpointed
model boundary, and cannot answer a question, grant permission or release a human barrier.
Stop batches terminal activity before deferred ledger cleanup, cancels owned command trees,
and prevents cancelled file replacements. Preserve original provider/vault/worktree identity,
registered-secret redaction, disabled inherited tracing and the documented workspace-jail
race/alias limitations; this remains an application boundary rather than an OS sandbox.

The shared PlanChecklist, step/Thinking/delegate disclosures, right-panel telemetry,
planning settings and editable running composer consume engine events. Latest-request
context occupancy is distinct from cumulative run tokens; estimates and fallback windows
are marked. Summary notices derive from actual installed summarizer transitions. Unavailable
budgets and fix counters are explicit. Phase 7 supplies verification/test detection, bounded
self-correction, enforced budgets and the context-ring/compaction policy; none of those
later-phase features is claimed by Phase 6. Phase 5 question/exhaustion contracts remain
available for its unknown-test-command and retry/change/stop flows.

## Phase 7 handoff to Phase 8

Phase 7 is complete; validation, installed-runtime contracts and the defects found by the final gates are recorded in
`2026-10-24-phase-7-verify-context/validation.md` and `learnings.md`. Phase 8 inherits a middleware stack whose order is
already load-bearing: the permission barrier stays the only human barrier, the verify gate sits after it and decides only
from `ToolMessage` outcomes, and the budget counter sits in `abefore_model`. `load_skill` and the Customize surface must
join that stack as read-only effects, or the gate will demand a verification command for reading a skill file.

The gate treats a *successful mutation* as the trigger, so any new write-capable tool (skill install from folder/zip/git,
marketplace catalog writes, MCP connector edits) is automatically covered by it and by the per-step fix budget. Those
installs are configuration changes: reuse the protected-configuration approval path that Phase 7's settings already use
(review → exact bytes → atomic write), rather than inventing a second approval surface. Unknown-command questions keep
using `ask_user_question` (D25) and the Phase 5 exhausted card, whose `presentation: "exhausted"` contract is unchanged.

Terminal and test results are reusable as-is for skill scripts and eval runs: `TerminalPanel` is output-only and takes a
payload, `TestResults` matches a `test.result` by `call_id`, and the timeout variant already carries the longer-timeout
approval. The Settings screen renders sections 1–4 (models, appearance, permissions, context/terminal) and defers the rest;
Phase 8's Customize hub is a separate screen, so it should reuse the section/row primitives and the inline approval card
rather than extend `settings-screen.tsx`.

Preserve the invariants Phase 7 relies on: detection never leaves the workspace and never executes anything; the
summarizer's private `.harness/context/` route stays read-only for everything else; the summary file is redacted and
bounded; breakdown rows are estimates while the ring total is provider usage; and every gate/budget decision is
reconstructable from persisted events so recovery after a crash is unchanged. The documented workspace-jail limits are
inherited unchanged — this remains an application boundary, not an OS sandbox.

## Phase 8 handoff to Phase 9

Phase 8 is complete; the validation record, the installed contracts it used and the defects the walkthrough found are in
`2026-10-25-phase-8-skills-customize/validation.md` and `learnings.md`. Phase 9 is `render_ui` plus polish: model-composed
GenUI, themes, fa/en coverage, empty and error states, shortcuts, accessibility, and the remaining Settings sections
(appearance, permissions, data and privacy, about).

What Phase 9 inherits and should reuse rather than re-invent:

- **The Customize hub** (`src/components/customize/`) is the working pattern for a tabbed screen: one screen with
  `data-testid="customize-tab-<tab>"`, a `src/i18n/<area>.ts` copy module with `en` and `fa` typed against each other, a
  `use-<area>.ts` hook per tab, and pure helpers in `src/lib/<area>.ts` covered by `tests/unit`. New settings sections
  should follow it; `settings-screen.tsx` is a section list, not a template for a hub.
- **The staged-approval contract.** Every mutation — skill install/create/edit/delete, search settings, MCP add/update/
  delete, agent create/edit/delete, memory — returns an `ApprovalRecord`, shows "waiting for approval in the inbox" in the
  surface that proposed it, and applies only after `POST /runs/{run}/interrupts/{id}`. Dialogs must stay open with that
  note; closing on a proposal hides the only explanation the person gets. The reviewed bytes are the validated bytes.
- **The audit artefacts.** `runs/<id>/request.json` (what the person asked), `system.md` (the prompt the model received),
  `activation.md` (what a slash command added) and `provider.json`. Phase 9's `render_ui` output should be reconstructable
  from persisted events the same way, or it is not evidence.
- **The composer's dynamic picker** (`src/lib/use-commands.ts` + `src/lib/commands.ts`) already filters a fetched command
  list with a keyboard contract (Arrow keys move, Enter picks the highlighted item, Escape dismisses). Reuse it for any new
  inline trigger rather than adding a second picker.
- **`ContextBreakdown.skills` / `.memory`** are measured blocks subtracted from the system row, so the five rows still add
  up to the prompt the model received. Keep that arithmetic if Phase 9 adds a row.

Invariants Phase 9 must not break: only `name — description` of a skill is ever in the prompt (the body arrives as a tool
result); `load_skill` and `web_search` stay non-mutating for the verify gate while `web_search` stays `ask` even in Auto;
MCP tools keep the `server__tool` namespace and go through the same permission barrier (a connector can never widen a
mode); a workspace agent stays a prompt plus the read-only ceiling, intersected in the loader, the factory and the
middleware; memory is read-only to the agent and written only by an approval; and `npm run build` must precede any desktop
suite, because Electron serves the static export from `out/`.

## Phase 9 handoff to Phase 9b

Phase 9 is complete; the validation record, the installed contracts it used and the defects the walkthrough found are in
`2026-10-25-phase-9-render-ui-polish/validation.md` and `learnings.md`. Phase 9b is the Schedule tab; Phase 10 is
packaging and evals.

What Phase 9b inherits and should reuse rather than re-invent:

- **The schedule empty state already exists.** `EmptyState` in `src/components/states/empty-state.tsx` with
  `statesCopy(locale).noSchedules` is built and tested (`tests/unit/states.test.ts` asserts it is the one state no screen
  reaches yet, via `WIRED` in `src/lib/states.ts`). Wiring the tab means changing that one entry from `null` to the
  component and deleting the test's allowance — not writing new copy.
  **Corrected by Phase 9b: it did need new copy.** The help line said this build has no scheduler, which was true then
  and false once the tab existed, and the primary action had to become "Add a schedule". Wiring the state was one line;
  telling the truth in it was not.
- **The settings section pattern.** A tab is `src/i18n/<area>.ts` (`en` typed against `fa`), a `use-<area>.ts` hook, pure
  helpers in `src/lib/<area>.ts` covered by `tests/unit`, and `data-testid` per control. `i18n.test.ts` discovers copy
  modules automatically, so a new one is covered the day it is written — and it will fail if a Persian literal appears in
  a component.
- **The staged-approval contract** still applies to a schedule that writes. Queued approvals from a scheduled run arrive in
  the same inbox, and the inline `ApprovalCard` is what the proposing surface shows.
- **`tests/phase9-desktop.ts`** is the template for a walkthrough: launch, assert on the DOM, collect evidence, never
  screenshot-and-hope. It also shows how to prove persistence (three launches on one profile) and how to prove a restart
  (kill the engine's children, wait for the card, restart, then use the app).

Invariants Phase 9b must not break: `render_ui` stays read-only and absent from the always-ask list; the always-ask list
stays engine-owned and five rows long (adding a sixth means changing the middleware, not the screen); every colour comes
from a palette token and every size from the `--fs-*` scale (`tests/unit/theme.test.ts` reads the stylesheet as data); no
physical CSS property anywhere (`tests/unit/logical-css.test.ts`); every key mapping goes through `src/lib/shortcuts.ts`;
and every user-visible string lives in `fa`/`en` with the same shape, the same placeholders and Persian digits in Persian.

## Phase 9b handoff to Phase 10

Phase 9b is complete; the validation record, the defects its walkthrough found and the decisions it made are in
`2026-10-25-phase-9b-schedule/validation.md` and `learnings.md`. Phase 10 is packaging and evals.

What Phase 10 inherits and should reuse rather than re-invent:

- **Scheduling is a loop in the engine, not a service.** `Scheduler.begin()` runs in the FastAPI lifespan and
  `close()` cancels the loop *and* its watchers. A packaged build inherits this for free, and nothing needs installing
  on the machine. If Phase 10 adds a watchdog, the scheduler must stay inside the engine process so the "app open only"
  promise survives it.
- **The app-data folder is now the only durable store**, and it holds schedules too. The Data screen's summary and the
  danger zone already cover it; a backup or an installer upgrade has one folder to preserve, not two (D34 — still
  pending approval, because the constitution names an SQLite file).
- **`tests/phase9b-desktop.ts` is the walkthrough pattern for a time-based feature**: four launches on one profile, a
  stored record edited between launches to simulate "the app was closed when it was due", and assertions read back from
  `catalog.json` rather than only from the DOM. Phase 10's evals should keep that shape — a schedule is the one feature
  whose evidence has to include the file on disk.
- **`[dir="rtl"]` mirrors a centred dialog** (D44). Any new modal Phase 10 draws needs the same line, and
  `tests/unit/logical-css.test.ts` will say so if it is forgotten.

Invariants Phase 10 must not break: a scheduled run is an ordinary run — its own `events.jsonl`, its own task, its own
approvals in the same inbox; full access never bypasses the always-ask list; a missed occurrence is never started
silently; and every dialog, screen and string keeps the fa/en parity the parity test enforces.

## Audit log (D20): the mock wins

The mock was left exactly as sketched. These spec statements were changed to match it:
- Permissions: the always-ask list shows the engine's **five** rows, not the mock's three. The mock's three keep their order and MCP tool calls and long timeouts follow, because showing three would tell the person those run unattended in Auto (D10, Decision 10).
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
