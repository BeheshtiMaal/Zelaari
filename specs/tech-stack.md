# Tech Stack

## Shape (mirrors onboard-harness)
```
Electron (Windows x64)
 ├─ electron/        main process: window, sidecar lifecycle, safeStorage, native dialogs, preload
 ├─ src/             Next.js 16 + React 19 UI, statically exported and loaded by Electron
 └─ backend/         Python 3.12 engine (FastAPI + deepagents + LangGraph + SQLite)
                     bundled with PyInstaller; listens on 127.0.0.1 with a per-launch secret
```
Single-user, fully local, no server, no account. The only network traffic is the conversation with the model the user configured
(plus the optional web skill).

## What we take from onboard-harness, and what changes
| Area | onboard-harness | CodeHarness |
|---|---|---|
| Product | office agent for non-technical teams | coding agent for developers |
| Folder layout | `backend/ build/ electron/ public/ scripts/ src/ docs/ .github/workflows/` + `AGENTS.md SECURITY.md electron-builder.json` | same layout, same names |
| UI stack | Next.js 16, React 19, Tailwind v4, Radix, Phosphor icons, zustand, Vazirmatn font | same, plus OpenUI GenUI, diff viewer, xterm.js |
| Locale | Persian RTL only | Persian (RTL) default + English, RTL-safe by construction |
| Pages | Home, Tasks, Approvals inbox, Files, Customize, Settings | New task (home), Run (Tasks), Approvals inbox, Workspace (files and tasks together, no separate Files page), Customize hub, Schedule, Settings |
| Workspace | a folder; system files in `.harness/` (agents, skills, rules, memory, run history) | same idea (layout below) |
| Modes | "with approval", "auto", "read-only" | Ask (default), Auto, Read-only |
| Permissions | per tool and per folder: allow / ask / deny | same |
| Approvals | approve, edit input, reject with reason | same, with unified diff for edits and risk badge for commands |
| Safety | workspace-only, rules file protected, budgets, event log, resume, keys in OS vault, loopback + token | all adopted |
| Models | user-defined (base URL, key, model), OpenAI- or Anthropic-compatible, demo model | same |
| Packaging | electron-builder NSIS + zip, PyInstaller engine | same |
| Evals | 66-case suite with real model | smaller suite first (fake + live), grows per phase |
| License | AGPL-3.0 | MIT; no code copied |

## Frontend
- Electron (stable), electron-builder (NSIS per-user installer + portable zip, unsigned; README explains SmartScreen).
- Next.js 16 static export, React 19, TypeScript strict, Tailwind v4, Radix UI, Phosphor icons, zustand.
- i18n: `fa` and `en` dictionaries; CSS uses logical properties (`margin-inline-start`, etc.); **default is Persian on first launch**; the language switch lives in Settings > Appearance (Persian / English) and the choice is remembered; Vazirmatn bundled.
- Light and dark theme.
- **OpenUI**: `@openuidev/react-lang` (parser, `Renderer`, prompt generation) + `@openuidev/react-ui` styles. React 19 is required and satisfied.
- Diff view: `diff` library + custom component. Terminal output: xterm.js, read-only.

## Engine: built on deepagents
We use `deepagents.create_deep_agent(...)` as the harness instead of writing a bare LangGraph. It already provides, and we reuse:
planning (`write_todos`), filesystem tools (`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`), shell (`execute`),
sub-agents (`task`), context management (offload + summarization), memory, skills, and human-in-the-loop interrupts, all on LangGraph
with SQLite checkpointing.

Wiring:
```python
agent = create_deep_agent(
    model=<chat model from provider record>,
    system_prompt=<ours; fully replaces the default>,
    backend=<workspace-jailed filesystem + local shell backend>,
    tools=[ask_user_question, submit_plan, render_ui, load_skill?],
    subagents=[reviewer (read-only), researcher (read-only)],
    skills=[workspace .harness/skills, user skills, bundled skills],
    memory=[workspace .harness/memory.md],
    middleware=[PermissionMiddleware, PlanGateMiddleware, VerifyGateMiddleware, BudgetMiddleware, EventMiddleware],
    checkpointer=SqliteSaver(...),
)
```
Notes to confirm in the Phase 0 spike (do not assume): exact `create_deep_agent` kwargs for skills/memory/middleware in the installed
version; whether the stock local shell backend behaves on Windows (PowerShell). If not, we ship our own `run_command` tool and disable `execute`.
deepagents follows a "trust the LLM" model, so **all boundaries are enforced in our tool layer, never by prompting**.

Providers (`backend/providers/`): a provider record is `{name, base_url, api_key_ref, model, kind (inferred), context_window (auto-detected), supports_tools}`.
`langchain-openai` and `langchain-anthropic` back them. DeepSeek, GLM, AvalAI and any other OpenAI-compatible service are records with a different base URL.
There are **no price fields, no manual context field and no kind toggle**; the meter shows tokens only.
- **Add-model dialog** (dimmed backdrop, rounded card): name, Base URL, preset buttons under the URL box (OpenAI, Anthropic, Jev, AvalAI, Metis) that fill the URL,
  API key, model name. `kind` is inferred: the Anthropic preset or an `api.anthropic.com` URL means native Anthropic; anything else is OpenAI-compatible.
  Presets live in `backend/providers/presets.json`. Verified: AvalAI `https://api.avalai.ir/v1`; OpenAI `https://api.openai.com/v1` and Anthropic
  `https://api.anthropic.com` are the standard endpoints. **Open: the Jev URL and the Metis OpenAI-compatible URL (see roadmap).**
- **Test connection** makes a tiny tool-call probe because the harness needs tool calling; models without it are rejected.
- **Context window detection** (in order): provider `/models` metadata if it carries a context length; a built-in table by model name (shipped with the app);
  the limit parsed from a context-length error message; otherwise a conservative 32K shown as "~". The ring and compaction use this value.
- A scripted **demo model** works offline with no key.

## Permissions and HITL (same model as the repo)
- **Modes** (chosen per conversation): **Read-only** (no writes, no commands), **Ask** (default), **Auto**.
- **Rules**: per tool x path glob -> `allow | ask | deny`, stored in `.harness/rules.json`, editable in Customize. Defaults: reads allow, writes ask,
  commands ask, web ask, protected paths deny/ask (below).
- **PermissionMiddleware** is the single authority. `deny` returns a tool error the model can read. `ask` raises a LangGraph interrupt with an
  approval payload. `allow` proceeds. We do not depend on static per-tool interrupt config because our rules are path- and command-aware.
- **Decisions**: approve, edit input then approve, or reject with a reason (returned to the model as the tool result, run continues).
- **Always ask, even in Auto**: every web-search query (unless the user sets an explicit allow rule), changes to `.harness/rules.json`, edits to `.harness/` system files, commands classified high-risk (this includes recursive deletes).
  File deletion defaults to `ask`. The mock's rules table shows a user-set `deny` for deletion as an example of a customized workspace.
- **Command risk classifier** (patterns, tested): recursive/forced delete, disk/format ops, registry edits, encoded PowerShell, pipe-to-shell downloads,
  `git push --force`/`reset --hard`/`clean -fd`, package install/uninstall, network tools, anything resolving outside the workspace.
- **Workspace jail**: resolve real paths (symlinks and junctions) and reject escapes. Whole drives or the home folder cannot be a workspace.
- **Secrets**: API keys live in Electron `safeStorage` (DPAPI), handed to the engine in memory, never in the workspace, scrubbed from the environment
  of every spawned command. Executables inside the workspace are never run by a UI click.
- **Atomic writes**: files are written to a temp file and renamed, so an API error or a crash never leaves a half-written file.
- **Crash safety**: after an engine crash, a tool call that was in flight is never replayed automatically; it is marked interrupted, shown to the user, and reported to the model.
- **Undo**: every write snapshots the previous content to `.harness/snapshots/` so any change can be reverted from the UI.

## Planning and the plan gate (user decision: "B")
1. The agent analyzes (read-only tools allowed), then calls `submit_plan`: ordered steps, each with a title, optional file globs it expects to touch,
   and an optional verify command. Progress afterward uses deepagents' `write_todos`; the engine mirrors both into `plan.created` / `plan.step.updated`.
2. **Plan approval is required only for bigger plans**: 4 or more steps, OR more than 3 expected files, OR any step flagged high-risk.
   Smaller plans run immediately and are shown live. The step and file thresholds are settings (Settings > Permissions); the high-risk trigger is fixed. In **Auto** mode the plan gate is off.
3. **Deviation gate** (the brief's "leaving the plan"): if the agent wants to touch files outside the plan's declared globs, add more than 2 steps,
   or drop an approved step, it raises an approval with the diff of the plan. Applies in Ask and Auto (setting, default on).

## Verification and self-correction
- **Test command**: auto-detect **pytest** (`pyproject.toml`, `pytest.ini`, `tests/`) and **npm test** (`package.json` scripts.test).
  Otherwise use the project setting; otherwise the agent asks via a QuestionCard. No other runners in v1.
- **Verify gate** (structural, not a prompt rule): if files changed and no verification command has run successfully since the last change, the agent
  may not finish; the harness injects "run the checks" and continues. Decision is based on tool-call results, not on what the model claims.
- **Reflect loop**: on failure the agent reads the output and decides fix vs. re-plan. Limits: 3 fix attempts per step, global caps on steps and wall time.
  On exhaustion it stops and asks the human (QuestionCard: retry with hint / change approach / stop).
- **Quality**: system prompt rules (small modules, tests with changes, no dead code, follow existing style) + the `python-project` skill (a `node-project` skill is backlog).
- **Metering** (user decision: "A"): show tokens used; if the provider does not report usage we estimate and mark it with "~". No cost display (price fields were removed). Hard limits never depend on usage data.

## Skills (same as the repo: folders, on demand)
- Folder: `SKILL.md` (frontmatter `name`, `description`; body = instructions) + optional `scripts/`, `references/`.
- Locations: workspace `.harness/skills/`, user `%APPDATA%/CodeHarness/skills/`, bundled `skills/`.
- Optional frontmatter `command: /grill` gives a skill a slash command shown on its card and in the `/` picker.
- Progressive disclosure: only name + description reach the prompt; body loads when the agent decides it is relevant.
- Skill scripts run through the same command tool and permission layer. Installing a skill (folder/zip/git URL) is itself an approval.
- **Skills tab** (inside the **Customize** hub, WorkBuddy-style): tabs *Installed / Marketplace / Mine* (Persian UI: نصب‌شده / بازار مهارت‌ها / ساخته‌شده توسط من), search + category chips, a card per skill (name, description,
  source badge, slash command, security-scan status, context cost in tokens, on/off switch), a detail panel showing `SKILL.md`, and
  *Import from folder, ZIP or Git* plus *Create skill*. Enabling a skill is per workspace. Installed skills are scanned before first use (scripts listed, risky patterns flagged).
  *Marketplace* in v1 is a catalog file (JSON index) in a public Git repo; installing a skill is a git clone or ZIP download plus the approval and security scan above.
  No accounts, no payments, no hosted server.
- Bundled (installed on first run): `grill-me` (`/grill`), `feature-spec` (`/spec`), `fix-failing-tests` (`/fix`), `python-project`, `web-search` (`/search`). `web-search` ships enabled; each query appears in an approval card (approve, edit the query, or reject) before anything leaves the machine.
  `read-framework-docs` is an example project-level skill (source badge "project folder", off by default) that shows how a user adds their own skill under `.harness/skills/`. All skills show their context cost in tokens.

## GenUI (OpenUI)
1. **Deterministic UI for harness events**: the engine emits typed events; the UI maps them to OpenUI components. Works even with weak models.
2. **Model-composed UI** via `render_ui`: the model writes OpenUI Lang restricted to our component library (prompt generated from the library);
   output is parsed and validated; failure falls back to markdown and sends the model a short error.
- Library (Zod-defined): `QuestionCard`, `PlanChecklist`, `ApprovalCard`, `DiffView`, `TerminalPanel`, `TestResults`, `FileTree`, `Callout`,
  `Stack`, `Tabs`, `Table`, `KeyValue`. Interactions (answer, approve, edit, reject) POST back to the engine.
- **AskUserQuestion**: tool `ask_user_question` takes 1 to 3 questions; each has a short header, text, 2 to 4 options with descriptions,
  `type: single | multi | rank`, and a free-text "Other" always available. Returns structured answers to the model. Dismiss returns "declined".
  The tool description teaches the model to ask only when the answer cannot be found by reading the project.
- Aesthetics: bold rounded cards, clear hierarchy, keyboard shortcuts (1-4, Enter, Esc), light/dark, RTL-correct, accessible (focus, ARIA).

## Chat box and context window (inspired by WorkBuddy and similar agent apps)
The composer is a large rounded card. Placeholder: `@` adds context, `/` enables skills and commands. Toolbar (one row in a running task): `+` (menu: add workspace files, insert a skill), git branch,
permission mode, then on the other side the **context ring** (a small arc, no text), the **model selector** and the round send button. On the home screen the
workspace, branch, **Worktree** checkbox and permission mode sit in a second bar under the card. The branch chip shows the current branch (read from `.git/HEAD`, hidden if the
folder is not a git repo); switching runs `git switch` through the permission layer (approval). **Worktree**: when checked (git repos only, git installed), the task runs in a
separate `git worktree` under `.harness/worktrees/<task-id>` so the main checkout is untouched; creating it is an approval, and the user merges the result themselves. **Hovering the ring shows a tooltip** such as
"38% · 48.8K / 128.0K context used". Clicking the ring opens a breakdown:
messages, tool results, system prompt + tools, active skills, memory, with a marker at the auto-compaction threshold (default 60%, setting) and a
"new chat with summary" action. Numbers come from the provider's usage when reported, else a local estimate marked "~". The model's context window size
is the auto-detected value on the model record. The breakdown popover is specified here but not drawn in the mock. This pairs with deepagents' summarization/offload and the `context.summarized` event.

## Connectors (MCP)
The Customize hub has a **Connectors** tab for MCP servers (the tab is in the mock; its inner screen is not drawn). Each server is a card (name, command or URL, status, tool list).
Tools are loaded through an MCP adapter (`langchain-mcp-adapters`), namespaced `server__tool`, and every call goes through PermissionMiddleware (default `ask`). Adding a stdio server
is itself a command-execution approval. Config lives in `.harness/mcp.json` (workspace) and the user config; secrets are never written to the workspace.

## Approvals inbox
Two-pane screen: list of pending approvals (type icon, title, source task or schedule, risk chip, in-plan chip, command preview) and a detail pane.
Detail for a file edit: reason from the agent, unified diff with line numbers, snapshot note (undo), checkbox "don't ask again for `src/**`" which writes an allow rule,
optional rejection reason (sent back to the model), buttons Approve / Edit input / Reject with reason, keyboard Enter / Esc. Tabs: Pending / Approved / Rejected / All.
Recent decisions stay listed (dimmed) for audit. The sidebar badge shows the pending approval count across all tasks and schedules (questions are not counted; they mark their task with the amber dot).

## Settings
Sections (all seven drawn): **Models and keys** (provider cards with base URL, model, auto-detected context, key status, tool-call test, default model; Add model opens a dialog), Appearance and language, Permissions and safety (default mode, plan-gate thresholds, deviation gate, protected paths), Context and compaction, Terminal and tests
(test command, shell), Data and privacy (where `.harness/` data lives, clear history), About. Pinned at the bottom of the sidebar with a gear icon.
Keys are shown masked (last 4 only) and stay in the Windows vault.

## Scheduled tasks (WorkBuddy-style Schedule tab)
Sidebar item **Schedule**: list of active schedules (workspace, repeat, time, permission mode, last result, on/off switch), popular templates
(nightly tests, daily git review, weekly dependency check, ...), and an **Add scheduled task** dialog: name, prompt, workspace, **mode** (the chip inside the prompt box: Read-only / Ask / Auto), **access ceiling** (the chip under it:
read-only and report, or full access shown in red), repeat, time, validity. The effective permission is the stricter of mode and access ceiling. Design rules (HITL-safe):
- The scheduler lives in the engine and **runs only while the app is open**; missed runs are offered as "run now" at next launch. No background service in v1.
- Unattended runs default to **Read-only + report**. Ask mode is allowed: approvals queue in the Approvals inbox until the user returns, and the run pauses.
- "Full access" (Auto) is selectable but shown in red with a warning; it never applies to the always-ask list (rules file, web search, high-risk commands).
- Each run is a normal run with its own `events.jsonl`; results appear as a task under the workspace.
- Schedules are stored in the app data database (`%APPDATA%/CodeHarness/app.sqlite`), not in the workspace `.harness/` folder.

## Navigation (sidebar)
Icon + label items: **New task**, **Approvals inbox** (badge), **Customize** (one hub with sub-tabs Skills / Agents / Rules and permissions / Memory / Connectors (MCP)), **Schedule**.
Below: **Workspaces** list; each workspace expands to its tasks. **Opening a workspace shows its files and its tasks together** (file tree, file viewer with
agent changes marked, task list). There is no separate Files page. **Settings** is pinned at the bottom with a gear icon.

## Visual shell
Dark theme by default (light theme supported). Sidebar slightly lighter than the content; the chat and side panel live in one inset, rounded surface (large corner radius where it meets the sidebar). Logical CSS only so the
shell mirrors correctly in RTL and LTR.

## Agent activity UI (deepagents has no UI; we build it)
deepagents is a library. The Tasks page renders one **activity timeline per run**, grouped by plan step:
- **Thinking**: collapsible panel fed by `reasoning.delta`, streamed live, auto-collapsed when the step ends. Shows only reasoning the provider
  actually returns (Anthropic thinking blocks, DeepSeek-style reasoning text, etc.). Reasoning is reported per step: if no reasoning arrived for a step, that step's row says "this model sent no reasoning" (providers may send it only on some turns).
  It never relabels normal output as reasoning. Provider differences are tested per provider in Phase 2.
- **Plan**: PlanChecklist with live status (pending / in progress / done / failed).
- **Actions**: tool-call lines, TerminalPanel, DiffView, TestResults.
- **Sub-agents**: nested, collapsible rows from the `task` tool (`subagent.started/finished`) showing what each delegate did.
- **Context**: a small notice when deepagents summarizes or offloads history (`context.summarized`), so the user knows why earlier turns were condensed.
- **Needs you**: an approval appears inline in the step and in the Approvals inbox (the inbox lists approvals only). A question (`ask_user_question`) is answered
  inline in its run. Several interrupts can be pending at once (parallel tool calls in one model turn can raise an approval and a question together); the run resumes when all
  are answered. A task waiting on anything shows an amber dot next to it in the sidebar (covers background and scheduled runs). The right panel counts what waits in the current task.
- Step cards: finished steps collapse to one line (duration, counts, thinking note); the active step is expanded with Thinking, sub-agent blocks and any pending approval.
  Sub-agent block: name, read-only badge, delegated task, its own mini timeline, final result, status/duration, collapsible. Several can run at once.
  Thinking panel streams with a caret; a step with no reasoning says so.
- Mid-run, the composer stays usable: a message steers the agent; the send button becomes Stop.

## Empty and error states
Empty (each with one clear next action): no workspace (pick folder / sample project), no model (add model / demo model), empty approvals, no schedules,
workspace with no tasks (suggestion chips), no skills enabled.
Errors (say what happened, what is still safe, what to do): model 401 / 429 with automatic backoff, engine crash (resume from the checkpoint; no half-finished command is replayed),
fix attempts exhausted (question card: retry with a hint / re-plan / stop and report), command timeout (process tree killed; longer timeout needs a new approval),
model without tool-calling (rejected at connection test), workspace-jail block (error returned to the model, run continues).


## Wire protocol
SSE events: `run.started`, `plan.created`, `plan.step.updated`, `message.delta`, `reasoning.delta`, `subagent.started`, `subagent.finished`, `context.summarized`, `tool.call`, `tool.result`, `approval.requested`,
`approval.resolved`, `question.asked`, `question.answered`, `ui.render`, `test.result`, `usage.updated`, `run.finished`, `run.error`.
REST: `POST /runs`, `POST /runs/{id}/messages`, `POST /runs/{id}/stop`, `POST /runs/{id}/interrupts/{iid}`, `GET/PUT /settings`,
`GET/POST /models`, `GET/POST /skills`, `GET/PUT /rules`, `GET /files`, `GET /approvals`, `GET/POST/PUT/DELETE /schedules`.
Every event is appended to `.harness/runs/<id>/events.jsonl`; unfinished runs resume from the SQLite checkpoint.

## Workspace layout (`.harness/`, inside the user's folder)
```
.harness/
  rules.json          permissions (allow/ask/deny)
  config.json         mode defaults, thresholds, test command, budgets
  memory.md           facts the agent should always know (loaded as memory)
  skills/<name>/SKILL.md
  agents/<name>.md    custom sub-agents
  runs/<id>/events.jsonl
  snapshots/
  checkpoints.sqlite
```

## Repo layout (same names as the reference)
```
codeharness/
  .github/workflows/     typecheck, lint, pytest, build installer
  backend/               engine: server/ agent/ tools/ permissions/ providers/ skills/ store/ evals/ tests/
  build/                 icons, installer assets, pyinstaller spec
  docs/screenshots/
  electron/              main.ts, preload.ts, sidecar.ts
  public/
  scripts/               build helpers
  skills/                bundled skills
  specs/                 this constitution and feature specs
  src/                   Next.js app: app/ components/ genui/ lib/ store/ i18n/
  AGENTS.md  SECURITY.md  README.md  LICENSE  electron-builder.json  next.config.ts  package.json
```
Commands: `npm run dev`, `npm run desktop`, `npm run desktop:preview`, `npm run desktop:build`, `npm run typecheck`, `npm run test:engine`.
Engine dev server: `python -m server --dev` (no token, loopback, dev only).

## Quality gates
`ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`, eval suite (fake model in CI, live model manually).
