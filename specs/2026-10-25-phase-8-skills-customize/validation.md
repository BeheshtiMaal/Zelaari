# Phase 8: Skills, Customize hub, Connectors. Validation

Every item is automated: engine behaviour by `pytest`, formatting and parsing by `npm run test:ui`, screens by a
Playwright-driven Electron suite (`tests/phase8-desktop.ts`) that runs the real preload, the authenticated loopback
engine and SQLite against a disposable workspace and profile, with offline scripted models. Screenshots are
evidence, never the assertion. Tick a box only with the test name or the evidence line that proves it.

## Automated: engine

- [x] R1 frontmatter accepts the mock's `grill-me` file (folded description) and rejects a bad name, a long
      description and an unknown key with a `problem`, never an exception — `test_skill_frontmatter.py` (7 tests)
- [x] R2 discovery merges the three roots with workspace > user > bundled precedence; a symlinked skill folder is
      ignored; 201 folders stop at the bound — `test_skill_loader.py`
- [x] R2 a missing workspace/user/bundled root yields an empty list, not an error — `test_skill_loader.py`
- [x] R3 the prompt block contains each enabled skill's name and description and no body text; it is ≤ 2 000
      characters and truncates with `…` — `test_skill_prompt.py::test_only_name_and_description_reach_the_prompt`,
      `::test_the_block_is_bounded_and_truncates`
- [x] R3 `load_skill` returns frontmatter + body + scripts, refuses an unknown, disabled or blocked skill, and its
      tool result never contains a secret — `test_skill_tools.py` (6 tests)
- [x] R3 a `load_skill` call does not arm the verify gate: a run that only loads a skill can finish without a test
      command — `test_skill_tools.py::test_load_skill_is_not_a_mutation_for_the_verify_gate`
- [x] R4 `PUT /skills/enabled` writes `.harness/skills.json` atomically, a disabled skill disappears from the
      prompt, the command list and `load_skill` — `test_skills_routes.py::test_a_switch_is_written_and_removes_the_command`,
      `test_skill_loader.py`, and the walkthrough's S3 (prompt of the next run)
- [x] R5 the scan flags each pattern id and blocks `rm_rf` / `pipe_to_shell`; a blocked skill cannot be installed
      or loaded; re-scanning an edited body drops the old verdict — `test_skill_scan.py` (6 tests),
      `test_skill_install.py::test_candidate_refuses_a_blocked_skill`,
      `test_skill_tools.py::test_a_blocked_skill_is_not_loaded`
- [x] R6 install from a folder and from a ZIP produce a proposal, not a write; approving writes every file
      atomically and rejecting writes nothing — `test_skills_routes.py::test_install_is_a_proposal_and_approving_writes_it`,
      `::test_rejecting_an_install_writes_nothing`, `::test_a_zip_install_works`
- [x] R6 a ZIP with `../`, an absolute entry, a symlink entry, > 200 entries or > 8 MB is refused before any
      proposal — `test_skill_install.py` (traversal, symlink, count and size cases)
- [x] R6 installing a name that already exists in that root is refused with 409 — `test_skills_routes.py::test_a_duplicate_install_is_refused`
- [x] R7 create, edit and delete are proposals; a bundled skill cannot be edited or deleted —
      `test_skills_routes.py::test_create_edit_and_delete`, `::test_a_bundled_skill_cannot_be_edited_or_deleted`
- [x] R8 the marketplace parser accepts the documented catalog and rejects a wrong version, > 200 entries and a
      non-https URL; a fetch failure keeps the cache and reports the error — `test_marketplace.py` (10 tests)
- [x] R9 the five bundled skills and the example project skill parse, scan clean and expose the documented commands
      — `test_bundled_skills.py` (5 tests), including `test_the_example_project_skill_is_off_by_default`
      (`examples/sample-project/.harness/skills/read-framework-docs`)
- [x] R10 every `web_search` call is `ask` in Ask and in Auto and `deny` in read-only, even with a `*` allow rule —
      `test_web_search_permissions.py` (4 tests)
- [x] R10 the DuckDuckGo parser turns the recorded fixture into ≤ 8 results with title/url/snippet; malformed HTML
      yields no results and a message, not an exception — `test_web_search.py` (13 tests)
- [x] R10 an edited query is re-validated (single line, ≤ 400 characters) and is the text that reaches the provider
      — `test_web_search_permissions.py` and the walkthrough's S4, where a local SearXNG-shaped endpoint received
      only the edited query
- [x] R11 `.harness/mcp.json` validation refuses a bad name, a missing command, a non-https URL and a secret value;
      `env_keys` never store values — `test_mcp_config.py` (10 tests)
- [x] R11 the stdio client initialises, lists tools and calls one against a fake server, and a timeout kills the
      process tree — `test_mcp_client.py` (14 tests, `mcp_worker.py` as the fixture server)
- [x] R11 MCP tools are named `server__tool`, carry their schema, are `ask` in Ask and Auto and `deny` in read-only;
      a broken server removes its tools without failing the run — `test_mcp_tools.py` (7 tests),
      `test_mcp_permissions.py` (7 tests)
- [x] R11 add/update/delete are approvals and apply only on approve — `test_connectors_routes.py` (15 tests)
- [x] R12 a custom agent with a write tool is rejected at load; a valid one joins the `task` allowlist and runs
      read-only — `test_agents.py` (14 tests)
- [x] R13 `PUT /memory` is an approval; the memory block is ≤ 4 000 characters and appears in the system prompt —
      `test_memory.py` (8 tests), `test_skill_prompt_integration.py::test_memory_reaches_the_prompt_after_the_skills_block`
- [x] R13 `ContextBreakdown.skills` and `.memory` are non-zero once a skill and memory exist and match the measured
      block sizes — `test_breakdown_skills.py` (5 tests)
- [x] R14 a leading `/search` activates the skill, emits `skill.loaded` and includes the body in one instruction;
      `/grill` still turns on the interview state machine — `test_skill_activation.py` (4 tests), plus
      `test_skill_prompt.py` for the envelope and `test_interview.py` for the interview
- [x] R16 the new event and models are in the generated protocol with no diff after regeneration —
      `npm run generate:protocol` run twice leaves `src/lib/protocol.ts` byte-identical
- [x] R18 no skill, install or MCP path reads or writes outside the workspace/app-data root; a secret in a skill
      body or a server `env_keys` value is redacted — `test_skill_tools.py::test_a_secret_in_the_body_is_redacted`,
      `test_mcp_config.py` (values refused, names only), `test_skill_install.py` (path refusal)

## Automated: UI unit

- [x] R15 card labels, badges and token text match the mock's copy for both locales — `tests/unit/skills.test.ts`
- [x] R15 the category chips and the search box filter the installed list, and the counts follow — same file
- [x] R15 an install payload is built with the right `kind` for folder, zip and git — same file
- [x] R11 the Connectors list namespaces tools and maps status to its label — `tests/unit/connectors.test.ts`
- [x] R14 the `/` picker filters a dynamic command list, picks on Enter and dismisses on Escape —
      `tests/unit/commands.test.ts`

## Automated: Electron walkthrough (`tests/phase8-desktop.ts`)

- [x] S1 the hub renders the five tabs and the Skills tab reproduces the mock: inner tabs with counts, search,
      five category chips, six cards, the `requires approval` chip on `web-search`, a switch on every card, the add
      tile and the detail panel with the four rows and the `SKILL.md` block —
      DOM assertions plus `artifacts/phase8/skills-tab-fa.png`
      (evidence: "S1 five tabs, six cards for 6 skills, five chips that filter, the needs-approval chip on
      web-search, a one-card project subset, and a detail panel with four rows and the SKILL.md body")
- [x] S2 installing a folder shows the approval in the inbox, approving makes the skill appear as installed with a
      clean scan, and the file exists on disk; rejecting leaves the folder absent — evidence line "S2 a folder
      install was a proposal (no folder on disk), approving wrote .harness/skills/changelog-writer with a clean scan
      and a ۷ count, rejecting left refused-skill absent"
- [x] S3 toggling a skill off removes it from `/skills/commands` and the prompt of the next run; a `demo skill load`
      run calls `load_skill`, persists `skill.loaded`, and the persisted `system.md` prompt contains the name and
      description but not the body — evidence line "S3 the switch removed /search and /notes from the commands, a
      disabled skill left the prompt, and demo skill load called load_skill: … the body marker arrived only as the
      tool result"
- [x] S4 in Auto, `demo web search` still raises an approval card; editing the query in the card and approving makes
      the provider receive the edited query (a local SearXNG-shaped endpoint records it) — evidence line "S4 in Auto
      the web_search call still asked; … the local provider received only "release note checklist for maintainers""
- [x] S5 adding a stdio MCP server raises an approval; after approving, the server card shows `connected` with its
      tools, and a `demo mcp call` run shows an approval card for `server__tool` — evidence line "S5 adding a stdio
      server asked for approval, the approved card showed متصل with fake__echo and fake__count, and a fake__echo
      call asked again before the server answered echo: ping"
- [x] S6 the Memory tab saves through an approval and the next run's prompt contains the memory text; the Agents tab
      lists a custom agent — evidence line "S6 memory saved through an approval appeared in the next run's prompt,
      and a workspace agent saved the same way joined the delegate list without widening its tools"

## Automated: gates

Run in this order on the settled source (`scripts/desktop-gates.sh` runs the desktop half and writes one log per
suite into `artifacts/phase8/`).

- [x] `ruff check backend` — All checks passed
- [x] `mypy --strict backend` (0 errors) — 191 source files
- [x] `pytest backend/tests` (all pass, log in `artifacts/phase8/pytest.log`) — 758 collected, 758 dots and no `F`
      in the log; the host's delete shim truncated the summary line, so the count is confirmed by `--collect-only`
- [x] `tsc --noEmit`
- [x] `npm run test:ui` — 88 pass
- [x] `npm run generate:protocol` leaves `src/lib/protocol.ts` unchanged after the last model edit — run twice,
      byte-identical
- [x] `npm run build`
- [x] `npm run build:electron`
- [x] `npm run test:desktop` (baseline shell) — "Desktop: Persian/English, real demo read + OpenUI, replay, auth,
      loopback, normal and forced cleanup passed." The first attempt died at launch before the window was ready
      ("unsettled top-level await" on `.app-shell`); the re-run on the same build passed, which is the documented
      launch flake, not a product failure
- [x] `tests/phase4-desktop.ts`, `tests/phase5-desktop.ts`, `tests/phase6-desktop.ts`, `tests/phase7-desktop.ts`
      still pass on the settled build — logs `artifacts/phase8/desktop-phase4*.log` … `desktop-phase7.log`
- [x] `tests/phase8-desktop.ts` — S1–S6 in one sequential run, `artifacts/phase8/desktop-phase8.log`

## Evidence log

| Check | Evidence |
|---|---|
| S1 | `artifacts/phase8/skills-tab-fa.png`; six cards, five chips, four detail rows, body visible only in the detail panel |
| S2 | `artifacts/phase8/install-staged-fa.png`, `installed-fa.png`; the staged note, then the folder on disk after approval, then absence after rejection |
| S3 | `system.md` of two consecutive runs (with and without the skill), one `skill.loaded`, one `load_skill` tool result carrying the body |
| S4 | `artifacts/phase8/web-search-approval-fa.png`; the local provider's recorded queries are exactly `["release note checklist for maintainers"]` |
| S5 | `artifacts/phase8/connectors-fa.png`, `mcp-approval-fa.png`; `fake__echo` / `fake__count` listed, then gated, then answered |
| S6 | `artifacts/phase8/memory-fa.png`, `agents-fa.png`; memory and agent in the next run's prompt |
