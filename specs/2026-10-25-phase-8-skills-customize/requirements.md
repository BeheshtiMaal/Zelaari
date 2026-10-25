# Phase 8: Skills, Customize hub, Connectors. Requirements

## Goal
Capabilities stop being code and become folders: a skill is a `SKILL.md` with a description, loaded only when the
agent needs it. The Customize hub lists what is installed, where it came from, what it may do, and lets a person
turn it on for one workspace, install another, or connect an MCP server. Nothing here widens the permission
boundary: a skill script still runs through `run_command`, a web query still asks, and an MCP tool is one more
tool the same barrier classifies.

## In scope
- Skill folder format, discovery in three roots, frontmatter validation, progressive disclosure.
- `load_skill` (read-only) and `web_search` (always asked) as real tools in the existing middleware stack.
- Per-workspace enable state, security scan, install from folder / ZIP / Git through the protected-configuration approval.
- Marketplace as a JSON catalog in a public Git repository, no server, no accounts.
- Five bundled skills with real content, plus `read-framework-docs` as an example project skill, off by default.
- Customize hub: Skills (Installed / Marketplace / Mine), Agents, Rules and permissions (Phase 4), Memory, Connectors (MCP).
- Connectors: `.harness/mcp.json`, stdio and HTTP JSON-RPC clients, tools namespaced `server__tool`, every call `ask`.
- Slash commands from skills in the composer `/` picker; active-skills chip.
- Real `skills` and `memory` rows in the context breakdown.

## Out of scope
`render_ui` and model-composed GenUI, themes, remaining settings, empty/error screens, schedule, packaging (their
phases). A hosted marketplace, accounts, ratings, auto-update of installed skills. MCP resources, prompts,
sampling and OAuth. A sandbox for skill scripts (they use `run_command` and its jail).

## Screens (mock is the source of truth)
`docs/mock-source/Skills.dc.html` (hub chrome, tabs, cards, detail panel), `Home.dc.html` and `Main.dc.html`
(composer `/` hint and chip row). The Connectors inner screen is not drawn by the mock; it is specified in R11 and
was approved by the person as "Skills-tab style: cards + detail".

## Functional requirements

**R1 A skill is a folder with a validated `SKILL.md`.**
`<skill>/SKILL.md` starts with a `---` frontmatter block. Keys: `name` (required, `^[a-z0-9][a-z0-9-]{0,63}$`),
`description` (required, 1–1024 characters, folded continuation lines joined with a space), `command` (optional,
`^/[a-z0-9-]{1,32}$`), `category` (optional, one of `coding | tests | web | docs | other`, default `other`),
`requires_approval` (optional bool, default false), `enabled` (optional bool, default true). The body is ≤ 32 000
characters. Only `scripts/` and `references/` are listed; any other file is ignored. A file that fails validation is
skipped and reported with a `problem` string; it never raises out of the loader. Parsing is a pure function with its
own tests (no YAML dependency: a bounded `key: value` subset, comments and blank lines allowed).

**R2 Discovery has three roots and a fixed precedence.**
Workspace `.harness/skills/`, user `<app data>/skills/`, bundled `<repo>/skills/`. A name found in a nearer root
replaces the farther one; the record reports `source: "workspace" | "user" | "bundled"`. Discovery is bounded
(≤ 200 folders, ≤ 64 KB per `SKILL.md`, depth 1) and never follows a symlink or junction. A missing root is empty,
not an error. The mock's six installed skills are the five bundled ones plus the example project skill.

**R3 Progressive disclosure is structural.**
The system prompt receives only `name — description` for each enabled skill, under a bounded `Skills` heading
(≤ 2 000 characters total; longer descriptions are truncated with an ellipsis). The body is returned only by
`load_skill`, which returns the frontmatter, the body (≤ 16 000 characters), the script list and any scan finding.
`load_skill` is a read-only effect: it is allowed without approval, and the Phase 7 verify gate never treats it as a
mutation. A test asserts that body text never appears in the prompt the model receives.

**R4 Enablement is per workspace and off means gone.**
`.harness/skills.json` holds `{"disabled": [name], "catalog_url": string | null}`; a skill whose frontmatter says
`enabled: false` starts disabled. A disabled skill is absent from the prompt, absent from the `/` picker, and
`load_skill` refuses it with a reason. `PUT /skills/enabled?workspace=` writes that file atomically and directly:
it stores UI state only, changes no tool permission, and the mock's switch is immediate. Installs, creates, edits,
deletes and MCP edits are different: they write capability files and go through R6/R7/R11 approvals.

**R5 Every skill is scanned before first use.**
The scan lists `scripts/` and searches `SKILL.md` and those scripts for stable ids: `rm_rf`, `pipe_to_shell`,
`invoke_expression`, `eval`, `base64_decode`, `sudo`, `chmod_777`, `execution_policy`, `absolute_path`,
`net_upload`. Result: `clean` (no findings), `flagged` (findings that need a person's eyes), `blocked`
(`rm_rf` or `pipe_to_shell`). `blocked` refuses installation and makes `load_skill` return a refusal. The scan is a
pure function over bounded text and is re-run on every load, so an edited skill cannot keep an old "clean".

**R6 Install from folder, ZIP or Git is always an approval.**
`POST /skills/install {workspace, kind, source}`. `folder`: an existing readable directory. `zip`: ≤ 8 MB, ≤ 200
entries, ≤ 64 KB per file, only `SKILL.md`, `scripts/**`, `references/**`, no absolute paths, no `..`, no symlink
entries. `git`: `https://` or `ssh://` URL, shallow clone into a temporary directory outside the workspace. In every
case the candidate is validated (R1) and scanned (R5) before a proposal exists. The proposal is a
protected-configuration approval (`tool: skill_install`, `path: .harness/skills/<name>/SKILL.md`, the SKILL.md diff,
the full file manifest in `args`) using the Phase 7 path: review → exact bytes → atomic write. Approve writes every
file atomically; reject writes nothing; a name that already exists in that root is refused with 409.

**R7 Skills can be created, edited and deleted from the hub.**
`POST /skills/create`, `PUT /skills/{name}`, `DELETE /skills/{name}` each produce the same kind of approval
(`skill_create`, `skill_edit`, `skill_delete`). Only workspace skills can be edited or deleted; a bundled or user
skill answers 409 with a reason. Deleting removes the folder only after approval.

**R8 The marketplace is a JSON catalog in a Git repository.**
`GET /skills/marketplace?workspace=` returns the cached catalog, the configured URL and `fetched_at`.
`PUT /skills/marketplace` validates the URL (`https://`, `http://` only for `localhost`, or `file://` for tests),
fetches it (≤ 512 KB, 10 s), validates `{version: 1, skills: [{name, description, command?, category?, url,
version?, author?}]}` (≤ 200 entries), caches it in `.harness/marketplace.json` and returns it. No hosted server, no
account, no ranking. Installing an entry is R6 with the entry's URL and the same approval and scan.

**R9 The bundled content is real.**
`grill-me` (`/grill`), `feature-spec` (`/spec`), `fix-failing-tests` (`/fix`), `python-project`, `web-search`
(`/search`, `requires_approval: true`) live in `skills/`. Each `SKILL.md` is specific, actionable and ≤ 200 lines,
and `grill-me` describes the Phase 5 interview contract it inherits. `read-framework-docs` ships in
`examples/sample-project/.harness/skills/` with `enabled: false` and is the example project skill.

**R10 `web_search` asks every time, even in Auto.**
The tool exists only while `web-search` is enabled for the workspace. Args `{query, limit ≤ 8}`. Its category is
`web`, which the Phase 3 grid already forces to `ask` in every mode unless an explicit `web_search` allow rule
exists, and to `deny` in read-only. The approval card shows the query as the command and the query in the args, so
the person can edit it; an edited query is re-validated (1–400 characters, single line) and that text is what runs.
Provider: DuckDuckGo HTML by default (keyless, approved by the person), `searxng` with an endpoint, or `none`
(tool answers with a configuration message). Settings live in `.harness/config.json` under `search` and are edited
through the existing verify-settings approval. Fetch is bounded (10 s, 512 KB, ≤ 8 results), the parser is a pure
function tested against a recorded fixture, and a parse failure is a tool error, not a crash.

**R11 Connectors are MCP servers with a namespaced tool surface.**
`.harness/mcp.json`: `{"servers": [{name, transport: "stdio" | "http", command: string[] | null, url: string | null,
env_keys: string[], enabled: bool}]}`. `name` matches `^[a-z0-9-]{1,32}$`; stdio needs 1–8 command parts ≤ 512
characters; http needs `https://`. `env_keys` are names only; values are read from the process environment when the
server starts, so no secret is ever written to the workspace. Add, update and delete are protected-configuration
approvals (`mcp_server_add`, `mcp_server_update`, `mcp_server_delete`) because starting a stdio server runs a
command. Tools are exposed as `server__tool`, carry the MCP description and input schema, and every call is
category `mcp` → `ask` in ask and auto, `deny` in read-only. `GET /connectors?workspace=` returns each server with
`status: connected | error | disabled`, its tools and its error text; `POST /connectors/{name}/test` connects and
lists. Connect is bounded (5 s, ≤ 64 tools); a broken server is reported and never breaks a run.

**R12 Custom agents are read-only delegates.**
`.harness/agents/<name>.md` has the same frontmatter shape (`name`, `description`, optional `tools` drawn from the
read-only set). Valid agents join the `task` tool's allowlist next to `reviewer` and `researcher` and run with the
read-only backend; an agent that asks for a write tool is rejected at load. `GET /agents`, `POST /agents`,
`PUT /agents/{name}`, `DELETE /agents/{name}` are approvals (`agents_update`). The Agents tab lists them with their
source and tools.

**R13 Memory is one bounded file the person owns.**
`.harness/memory.md` is text, ≤ 32 KB. `GET /memory` returns it; `PUT /memory` is an approval (`memory_update`).
Up to 4 000 characters are injected into the system prompt as `Workspace memory`; the `memory` row of the context
breakdown is the measured cost of that block, and the `skills` row is the measured cost of the skills block. Both
stop being zero, which is the Phase 7 handoff requirement.

**R14 Slash commands come from skills.**
`GET /skills/commands?workspace=` returns `[{command, name, description, requires_approval}]` for every enabled
skill with a `command`. The composer's `/` picker is fed by that list (plus nothing hard-coded): typing `/` filters,
Enter picks, Escape dismisses, and the picked command fills the box as `/command `. A leading `/command` at run
start activates that skill: the engine prepends one `[harness]` instruction naming the skill and containing its body
(the person asked for it explicitly), emits `skill.loaded`, and `grill-me` still turns on the Phase 5 interview
state machine. The composer shows a chip per skill that is enabled and has a command, and marks the active one.

**R15 The Customize hub matches the mock.**
Five hub tabs: Skills, Agents, Rules and permissions, Memory, Connectors (MCP). Skills inner tabs
`Installed (n)` / `Marketplace` / `Mine`; search box; category chips (All, Coding, Tests, Web, Docs); card grid
(name in mono, source badge, description, command chip, `requires approval` chip, footer `security ✓ · ~N tokens`,
switch); a dashed `Add skill` tile; a right detail panel with the workspace switch, description, rows
`Command / Source / Scripts / Context cost`, the `SKILL.md` block and `Edit` / `Delete`. Exact Persian strings are in
the appendix. Layout, radii, colours and copy follow `Skills.dc.html`; the rendered rows, labels and control values
are asserted in the Electron suite, not by inspection.

**R16 Wire and events.**
New event `skill.loaded {name, source, command, tokens}`. `ContextBreakdown.skills` and `.memory` become real
measurements. New models in `agent/events.py` and the `Protocol` envelope: `SkillRecord`, `SkillDetail`,
`SkillsResponse`, `MarketplaceEntry`, `MarketplaceCatalog`, `SkillInstallInput`, `SkillEnabledInput`,
`SkillWriteInput`, `AgentRecord`, `MemoryDocument`, `McpServer`, `McpTool`, `ConnectorStatus`,
`ConnectorList`, `CustomizeSettings`. `src/lib/protocol.ts` is regenerated, never hand-edited.

**R17 Quality gates.**
`ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`, `npm run test:ui`, `npm run build`,
`npm run build:electron`, `npm run test:desktop`, `tests/phase8-desktop.ts` and the phase 4/5/6/7 baselines are
green. Every validation item is automated (engine `pytest`, UI unit tests, Playwright-driven Electron); no check
depends on a person looking at a window.

**R18 Boundaries and privacy.**
Skill discovery, install staging, memory and MCP config stay inside the workspace jail or the app-data root;
symlinks and junctions are not followed; every read and every fetch is bounded. No secret appears in
`.harness/mcp.json`, skill files, events, logs or fixtures; the existing redactor covers tool results, approval
args and skill bodies. A skill script has exactly the permissions of `run_command`, no more.

## Decisions (also recorded in `roadmap.md`)
1. **Web search is DuckDuckGo HTML, keyless.** The person chose it over SearXNG and Brave; the parser is tested
   against a recorded fixture and its brittleness is documented in `learnings.md`.
2. **The Connectors inner screen reuses the Skills layout** (cards + detail panel); the mock only draws the tab.
3. **Enable switches are direct writes**, because they store UI state and grant nothing. Installs, creates, edits,
   deletes and MCP edits reuse the Phase 7 protected-configuration approval (review → exact bytes → atomic write).
4. **No MCP SDK dependency.** A bounded JSON-RPC 2.0 client over stdio and streamable HTTP lives in
   `backend/connectors/`, so the packaged engine grows by one small module instead of a dependency tree.
5. **`read-framework-docs` ships as an example project skill**, off by default, because the mock shows it with the
   `project folder` badge and a switch that is off.

## Open questions for the person
1. None blocking. Search backend and the Connectors layout were answered before implementation.

## Appendix: exact strings from the mock (Persian, RTL)
Hub: title `سفارشی‌سازی`; subtitle `کارهایی که عامل فقط وقتی لازم شد سراغشان می‌رود. فقط نام و توضیح در زمینه می‌ماند.`;
buttons `وارد کردن از پوشه، ZIP یا Git` and `ساخت مهارت`; tabs `مهارت‌ها` / `عامل‌ها` / `قوانین و مجوزها` /
`حافظه` / `اتصال‌ها (MCP)`.
Skills inner tabs: `نصب‌شده (۶)` / `بازار مهارت‌ها` / `ساخته‌شده توسط من`; search placeholder `جست‌وجوی مهارت…`;
chips `همه` / `کدنویسی` / `تست` / `وب` / `مستندات`; add tile `افزودن مهارت` / `پوشه‌ای با SKILL.md را اینجا رها کنید`.
Badges: `آماده`, `پوشه‌ی پروژه`, `نیازمند تأیید`; footer `بررسی امنیتی ✓ · ~۴۰ توکن`.
Detail: `دستور`, `منبع` (`آماده (همراه برنامه)`), `اسکریپت‌ها` (`ندارد`), `هزینه در زمینه` (`~۴۰ توکن`), `SKILL.md`,
`ویرایش`, `حذف`; workspace switch label `فعال در این فضای کاری`.
