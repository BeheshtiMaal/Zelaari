# Phase 2 learnings

Status: implementation delivered in ordered commits; all local checks pass and
evidence is recorded in `validation.md`. Live acceptance remains open. On 2026-10-19 the user
explicitly chose: “Complete local validation and leave unavailable live checks open.”
No external credential file was read for this phase's validation.

## Verified contracts and versions
- Electron 44.9.0 local declarations: `safeStorage.isEncryptionAvailable`,
  `encryptString`, `decryptString`; DPAPI is used on Windows. Radix Dialog 1.3.1
  supplies modal focus containment; explicit focus return handles dialogs opened
  without a Radix Trigger. Inputs have explicit accessible names/helper descriptions.
- deepagents 0.7.28, langchain-openai 1.7.2, langchain-anthropic 1.7.6,
  FastAPI 0.146.0, httpx 0.28.1. Native Anthropic's SDK uses httpx2 internally;
  native synthetic tests exercise that real SDK transport, not an imitation adapter.
- Private OpenAI conversion overrides were checked against installed signatures.
  `reasoning_content` must be preserved on full/streamed responses and sent back on
  subsequent tool turns; generic ChatOpenAI drops it. Native thinking blocks already
  survive the Anthropic adapter. Bridge extraction separates actual reasoning/text.
- Anthropic SDK `types/model_info.py` documents `max_input_tokens`; the detector
  reads that in addition to compatible `context_window`/`context_length` metadata.
  SDK `resources/models.py` and `_constants.py` verify `/v1/models` and API header
  `anthropic-version: 2023-06-01`. Metadata without a positive matching limit falls
  through safely rather than invalidating tool support.
- The intentionally small model-name table uses the official
  [GPT-4.1 model page](https://developers.openai.com/api/docs/models/gpt-4.1):
  1,047,576 context tokens, verified 2026-10-19. This is a sourced fallback entry,
  not a recommended/seeded provider. Mock model identifiers/limits are illustrations.
- Next.js 16.4.2 local static-export/page guides were read. The app stays statically
  exported, with client state and authenticated Electron/engine services. The dev
  MCP reported no compilation issues and routes `/` and `/tasks`. agent-browser
  0.39.1 repeatedly failed to communicate with its own daemon, including a clean
  named-session reopen; its browser/React inspection checks are not claimed passed.
  The independently required Electron tests exercise the actual delivery surface.
  The optional dev server was stopped to release resources during native validation.

## Secrets and persistence
- Electron owns `vault.json`, containing only safeStorage ciphertext. Engine
  `catalog.json` contains public model metadata, key digests for rotation detection,
  language/default selection and workspace/task index. Neither is in the workspace.
  Keys move through authenticated write-only memory handoff and never launch env/args.
- A digest comparison invalidates a probe when a saved key changes, including after
  restart. A probe finishing after a concurrent key/config edit cannot authorize
  the changed configuration. Existing runs retain their original adapter/credential.
- Event redaction alone was insufficient: provider content reaches checkpoints before
  UI events. The model middleware now redacts complete returned messages before graph
  persistence; independent stream buffers protect split reasoning/message secrets.
- The demo remains a fixed, keyless offline record. Its Edit control is disabled
  with explanatory help; cloud cards edit credentials without returning stored keys.
- Draft Test connection is side-effect-free and does not save a model/key. Saving
  a successfully tested draft repeats the small persisted-record probe, so success
  cannot be transferred to different configuration without verification. Untested
  saves remain visible but cannot run/default until tested.
- SDK retries are disabled; 429 has at most three total attempts with 2/4 second
  backoff. Retry state is polled for saved models. Errors never serialize provider
  exception text. Settings rejects untested/failed defaults.
- Canonical workspace checks are shared in a lightweight module, separately invoked
  by native Electron selection and engine requests. Branch metadata and stale recents
  refresh on retrieval. Reopening tasks reads jailed events; it never executes tools.

## Reasoning evidence matrix
| Adapter/provider | Local evidence | Live evidence |
|---|---|---|
| Offline demo | Real read-file run, marked usage estimate, no invented reasoning | Not applicable; offline |
| OpenAI-compatible / DeepSeek-style reasoning field | Actual SDK synthetic HTTP conversions, tool round trips, redacted reasoning and usage | Open at user request |
| Native Anthropic | Actual SDK tool probe and thinking/text stream fixtures, thinking present/absent | Open at user request |

No claim is made that an arbitrary compatible model supplies reasoning, supports
forced thinking, or reports token usage. Each missing usage turn uses a marked
estimate: accumulated input/output characters divided by four, rounded up, including
tool turns. This is coarse and is never shown as provider-measured usage or cost.

## Scope and handoff
- Local results: 40 engine tests, 8 UI unit tests, ruff, strict mypy (48 files),
  TypeScript, static export, Electron bundle, both native desktop suites and the
  rebuilt bundled-engine smoke check pass. Native window visibility was measured
  at 0.274 seconds (Persian) and 0.299 seconds (English). No remote CI run is claimed.
  Desktop screenshots/evidence are under ignored `artifacts/phase2/` and
  `artifacts/desktop.json`; the canary scan covered 72 persisted files without a match.
- PyInstaller reports missing optional `langchain.mcp`/`fastmcp` and `tzdata`
  collection warnings. They do not affect the tested phase's UTC events, demo or
  model/settings routes. Revisit MCP dependencies in Phase 8 and timezone data
  before scheduling; do not treat current smoke checks as validation of those features.
- Jev/Metis URLs remain unknown/disabled. No web-search backend is selected.
- Worktree and branch switching remain Phase 3; mode selection is recorded but all
  modes retain the existing read-only dispatch guard. Skills, approvals, planning,
  context accounting/compaction and other Appearance controls remain deferred as
  approved. No untracked implementation TODOs were introduced.
- Phase 3 inherits stable provider IDs, vault handoff, native/engine workspace
  validation, task replay, current branch metadata and recorded modes. Do not
  advance the roadmap phase while Phase 2 live acceptance remains open.
- Constitution files remain unchanged. `roadmap-proposal.md` contains the concrete
  status-only amendment for separate approval under AGENTS.md rule 5.
