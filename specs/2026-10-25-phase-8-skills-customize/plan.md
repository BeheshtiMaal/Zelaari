# Phase 8: Skills, Customize hub, Connectors. Plan

One commit per step. Steps 1–6 are engine, 7–9 are renderer, 10 is wire, evidence and docs. Every step ends with
its tests written and the gates it can affect re-run.

## Step 1: Skill format, loader, scan, prompt block
- `backend/skills/types.py`: `SkillRecord`, `SkillDetail`, `SkillProblem`, `SkillScan`, `SkillSource`,
  `SkillsState` (`.harness/skills.json`), `SkillSummary`.
- `backend/skills/frontmatter.py`: bounded `key: value` parser (continuations, comments, quotes) → `(meta, body)`;
  validation to `SkillRecord` or `SkillProblem`. No YAML dependency.
- `backend/skills/loader.py`: `discover(workspace, app_data, bundled)` with the three roots, precedence, bounds,
  no-link walking; `find(name)`, `enabled(skill, state)`.
- `backend/skills/scan.py`: script listing and the ten pattern ids → `SkillScan`.
- `backend/skills/prompt.py`: `skills_block(skills)` (name + description only, ≤ 2 000 chars), `estimate_tokens`.
- Tests: `test_skill_frontmatter.py`, `test_skill_loader.py`, `test_skill_scan.py`, `test_skill_prompt.py`
  (including "body text never reaches the prompt").

## Step 2: `load_skill`, `web_search`, permission and gate integration
- `backend/skills/tools.py`: `build_load_skill(registry)` returning body + scripts + scan note; refusal for
  disabled/blocked/unknown.
- `backend/skills/search.py`: `SearchSettings`, DuckDuckGo HTML parser (pure), SearXNG JSON parser, `search()`
  with httpx, bounds, injectable transport for tests.
- `backend/skills/websearch.py`: `build_web_search(settings, transport)` tool.
- `backend/permissions/rules.py`: `SKILL_TOOLS = {"load_skill"}`, `MCP` category, `web_search` stays `web`;
  `category_of` learns `__` names and `load_skill`.
- `backend/permissions/middleware.py`: allow `load_skill` outright; `tool_target` maps `web_search.query` to the
  command so the card shows and edits the query.
- `backend/verify/gate.py`: assert `load_skill` is not a mutation (test, no code change expected).
- Tests: `test_skill_tools.py`, `test_web_search.py`, `test_web_search_permissions.py`.

## Step 3: Enable state and read routes
- `backend/skills/state.py`: load/save `.harness/skills.json` atomically, merge frontmatter `enabled`.
- `backend/server/skills.py`: `GET /skills`, `GET /skills/{name}`, `PUT /skills/enabled`,
  `GET /skills/commands`, `GET/PUT /skills/marketplace`.
- `backend/skills/marketplace.py`: URL validation, bounded fetch (http/file), catalog validation, cache file.
- Tests: `test_skills_routes.py`, `test_marketplace.py`.

## Step 4: Install, create, edit, delete through the protected approval
- `backend/skills/install.py`: `read_folder`, `read_zip` (bounded, traversal-proof), `clone_git` (temp dir),
  `validate_candidate` → `SkillCandidate` (manifest of files).
- `backend/store/actions.py`: `propose_skill_install`, `propose_skill_create`, `propose_skill_edit`,
  `propose_skill_delete`; execution writes the manifest atomically, deletes a folder on approve.
- `backend/permissions/review.py`: review support for the four tools (SKILL.md diff, manifest digest).
- Tests: `test_skill_install.py` (zip traversal, size caps, git refusal offline, approval writes/refuses),
  `test_skill_actions.py`.

## Step 5: MCP connectors
- `backend/connectors/types.py`: `McpServer`, `McpTool`, `ConnectorStatus`, `ConnectorList`, config file model.
- `backend/connectors/client.py`: stdio JSON-RPC (`initialize`, `notifications/initialized`, `tools/list`,
  `tools/call`) with a 5 s bound and process-tree kill; HTTP transport via httpx.
- `backend/connectors/tools.py`: one LangChain tool per MCP tool, name `server__tool`, schema passthrough.
- `backend/server/connectors.py`: `GET /connectors`, `POST /connectors`, `PUT/DELETE /connectors/{name}`,
  `POST /connectors/{name}/test`.
- `backend/agent/factory.py`: accept connector tools; `backend/agent/bridge.py`: load enabled servers at run start,
  never fail the run.
- Tests: `test_mcp_client.py` (fake stdio server script), `test_mcp_tools.py`, `test_mcp_permissions.py`,
  `test_connectors_routes.py`.

## Step 6: Agents, memory, prompt and breakdown
- `backend/agents/loader.py` + `backend/agents/tools.py`: `.harness/agents/<n>.md`, read-only allowlist.
- `backend/server/customize.py`: `GET/PUT /memory`, `GET/POST/PUT/DELETE /agents`, `GET /customize`.
- `backend/agent/factory.py`: system prompt gains the skills block, memory block and custom agents; `Window`
  carries `skills`/`memory` costs so `ContextBreakdown` reports them.
- `backend/agent/bridge.py`: build the registry per run, wire slash-command activation, `skill.loaded` event.
- Tests: `test_agents.py`, `test_memory.py`, `test_skill_prompt_integration.py`, `test_breakdown_skills.py`.

## Step 7: Skills tab UI
- `src/i18n/customize.ts` (fa from the mock, en equivalents).
- `src/components/customize/customize-screen.tsx` (hub tabs; Rules tab reuses `RulesScreen`).
- `src/components/customize/skills-tab.tsx`, `skill-card.tsx`, `skill-detail.tsx`, `install-dialog.tsx`,
  `create-dialog.tsx`, `marketplace-list.tsx`.
- `src/lib/use-skills.ts`, `src/lib/skills.ts` (pure filters/formatting with unit tests).
- `src/app/customize/page.tsx` renders the hub; `src/app/globals.css` gains the mock's layout.
- Tests: `tests/unit/skills.test.ts` (filter, counts, token label, badge mapping, install payload).

## Step 8: Connectors, Agents and Memory tabs
- `src/components/customize/connectors-tab.tsx` (cards + detail, add dialog, test), `agents-tab.tsx`,
  `memory-tab.tsx`; `src/lib/use-customize.ts`.
- Tests: `tests/unit/connectors.test.ts` (tool namespacing, status labels, validation).

## Step 9: Composer slash commands and active skills
- `src/lib/commands.ts`: `commandMatches(task, commands)` over the fetched list; `use-commands.ts` keeps the
  keyboard contract; `composer.tsx` shows the picker and the active-skill chips.
- `src/lib/use-commands.ts` fetches `/skills/commands` for the selected workspace.
- Tests: `tests/unit/commands.test.ts` extended (dynamic list, filter, dismissal).

## Step 10: Wire, desktop suite, gates, docs
- `npm run generate:protocol` (new models and event).
- `tests/phase8-desktop.ts`: S1 hub and Skills tab match the mock; S2 install from folder → approval → installed,
  scanned, counted; S3 enable switch + `load_skill` run (progressive disclosure asserted on the persisted prompt
  and events); S4 `web_search` asks in Auto and the edited query is what runs; S5 MCP add server → approval →
  tool listed, call asks; S6 Agents/Memory tabs write through approval.
- `backend/tests/phase8_seed.py` (workspace with the example project skill and a fake MCP server).
- Full gates, `validation.md` boxes, `learnings.md`, `roadmap.md` row 8 and the Phase 9 handoff.
