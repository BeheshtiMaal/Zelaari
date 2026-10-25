# Phase 8 implementation evidence

Implementation and validation are complete on settled source; every validation box is ticked in `validation.md` with named
evidence. This file records what the phase learned — the installed contracts it leaned on, the fixture design, and the
defects the walkthrough found that no unit test would have.

## Installed contracts actually used

- **Progressive disclosure is a prompt decision, not a tool decision.** `Registry.block()` renders `name — description`
  only (bounded, `…` on overflow) and `load_skill` returns the body as an ordinary tool result. The proof is a
  *persisted* artefact: every run now writes `runs/<id>/system.md` (the exact system text it sent, redacted) next to
  `request.json`. `test_skill_prompt_integration.py` asserts the marker never appears there, and the walkthrough asserts
  it on a real run.
- **Slash-command activation has three artefacts, and they are not interchangeable.** `request.json` stays what the person
  typed (`/house tidy the README`); `system.md` stays the summary block; `runs/<id>/activation.md` is the envelope that
  actually entered the conversation. Collapsing them into one file would misreport the request, and leaving the envelope
  unpersisted made R14 unverifiable — the first version of the activation test read `request.json` and could not see the
  body at all.
- **`task_of()` is the contract that keeps scripted models working.** The activation envelope wraps the person's words, so
  every model that matches on the task text (demo, verify, planning, questions) must strip it first. Centralising the
  envelope in `skills/prompt.py` and the strip in `task_of()` is what made `/grill` keep working unchanged.
- **The permission barrier sees the edited args, not the original ones.** `POST /interrupts/{id}/preview` stores the edited
  arguments on the ledger record and re-prepares the review; `resolve` then carries them to the graph as `edited_args`,
  and `PermissionMiddleware.awrap_tool_call` overrides the tool call before the tool runs. That is why the UI's `decide()`
  must *not* send `edited_args` itself: the review is the single source of the edit, and a second channel would let a
  stale card apply a different value.
- **MCP without the SDK.** The `mcp` package is not installed, so `connectors/client.py` speaks bounded JSON-RPC over stdio
  (`initialize`, `notifications/initialized`, `tools/list`, `tools/call`) and reuses the existing `JobObject` containment
  for the process tree. A server that cannot start costs its own tools and never the run.
- **`shlex.split(posix=False)` then quote-stripping** turns a one-line form command into argv while keeping Windows paths
  with spaces intact. A form value is never `eval`'d and never shell-interpreted.

## Fixture design

- `backend/providers/skills_demo.py` adds `demo skill load <name>`, `demo web search <query>` and `demo mcp call
  <server__tool>` — one real tool call followed by a plain answer. The engine's own tools do the work, so the walkthrough
  tests `load_skill`, the real search client and the real connector, not a description of them.
- `backend/tests/phase8_seed.py` builds the workspace: a project skill (`release-notes`, `/notes`, category docs) whose body
  carries `BODY-MARKER-8f3a`, and a copy of `mcp_worker.py` as `tools/mcp_fake.py`. It then asserts through the product's
  own loader that the skill is discovered, clean, enabled and costs tokens — a fixture that fails loudly rather than a
  silently empty screen.
- The walkthrough runs a **local SearXNG-shaped HTTP server** on an ephemeral port and points the workspace's search
  setting at it (through the protected approval). That is what makes "the edited query is the one that runs" a real
  assertion: the server records what it received. The alternative — `CODEHARNESS_SEARCH_FIXTURE` — is offline but cannot
  observe the query.

## Defects the walkthrough found

- **A stale `out/` makes the suite test the previous build.** Electron serves the static export through `app://`, so a
  renderer change is invisible until `npm run build`. A count assertion read `۵` while the source said `۶`; the source was
  right and the build was old. Every renderer gate now ends with a build, and the walkthrough is only meaningful after it.
- **`editing` meant two things in the Agents tab.** The add button set `editing = true`, and `submit` chose `PUT` whenever
  `editing` was true, so creating an agent sent `PUT /agents/<name>` and got `409 Unknown agent`. Replaced by an explicit
  `mode: "create" | "edit" | null`; the name field stays read-only only when a document is selected.
- **A dialog that closes on a proposal hides the approval.** The Connectors dialog closed as soon as the proposal came
  back, so the person saw a form vanish and no "waiting for approval" note. Proposals leave the dialog open with the staged
  note, exactly like install and create.
- **`installedSkills` excluded the root every install writes to.** Installs land in `.harness/skills`, which is the
  workspace root, so the "Installed" tab hid the skill the person had just approved and the mock's `Installed (۶)` could
  never be reached. `Installed` is now everything available in the workspace; `Made by me` is the project subset.

## Test-infrastructure notes

- **Run the Python gate through `uv run`.** `backend/.venv/Scripts/python.exe -m pytest` does not put the venv on `PATH`,
  and `test_budget.py`'s real `pytest -q` then fails with `The term 'pytest' is not recognized`. That looks exactly like a
  regression in the run loop and is not one. `uv run --project backend pytest backend/tests` is the gate.
- **Two host shims are unrelated.** `CODEHARNESS_SAFE_DELETE_ENABLED` is this product's flag for its own delete tool;
  `next build` needs `CODEBUDDY_SAFE_DELETE_ENABLED=0` for the sandbox's delete shim, whose bulk-delete guard trips on
  `.next/` cleanup.
- **The inline run approval lives in `.timeline`, not `.compose-region`.** `.compose-region` only holds branch and worktree
  approvals; a run approval that never appears there is not a missing card.
- **Launch can fail once.** Two runs in this phase died at `page.setViewportSize` with "Target page, context or browser has
  been closed" before the window was ready, and the identical command passed on retry. Treat a launch-time close as a
  flake to retry once, not as a product failure — but never treat a *later* close that way.
