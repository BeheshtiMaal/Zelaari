# Phase 2 learnings

Status: implementation and all automated/manual acceptance checks passed.
The user initially requested local-only validation, then authorized the external Phase 1
credential file for both model families and requested all remaining checks. Live Home
acceptance and a separate native Anthropic Messages adapter run now pass. The roadmap
completion amendment was explicitly approved and applied; Phase 3 has not started.

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
| OpenAI-compatible / DeepSeek-style reasoning field | Actual SDK synthetic HTTP conversions, tool round trips, redacted reasoning and usage | AvalAI gpt-4o-mini: live probe/read/stream/replay/Stop passed; measured usage; no reasoning |
| Native Anthropic | Actual SDK tool probe and thinking/text stream fixtures, thinking present/absent | AvalAI claude-haiku-4-5 via native Messages SDK diagnostic: probe/read/stream/replay/Stop passed; measured usage; no thinking |

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
  validation, task replay, current branch metadata and recorded modes. The approved roadmap completion amendment records this handoff; Phase 3 has not started.
- The roadmap status/handoff amendment in `roadmap-proposal.md` was explicitly
  approved on 2026-10-19 and applied under AGENTS.md rule 5. Other constitution
  files, phase scope/order and provider inference remain unchanged.

## Authorized live checks (2026-10-19)
- External `phase1-provider.env` was read only after explicit user authorization.
  Its key stayed in memory; temporary workspace persistence scans found no key.
  No provider response bodies, exception diagnostics or credentials were recorded.
- `scripts/check_live.py` now reports sanitized context, usage and reasoning presence,
  verifies identical event replay, cancels a second run, and scans persisted files.
  The native override is diagnostic only, never saved as product configuration.
- AvalAI's [official SDK documentation](https://docs.avalai.ir/en/libraries) specifies
  native Anthropic base URL `https://api.avalai.ir` without `/v1`; the compatible
  base URL includes `/v1`. The same supplied key worked for both transports.
- Compatible gpt-4o-mini: metadata context 128,000, measured usage 4,406 input /
  63 output; native claude-haiku-4-5: fallback context 32,768 estimated, measured
  usage 6,771 input / 161 output. Neither run emitted reasoning/thinking.
- Exact-host Anthropic inference remains unchanged. The user requested both model
  families through the supplied compatible URL; both now pass actual Home acceptance.
  The native Messages transport is verified separately using an explicit diagnostic
  override. No direct api.anthropic.com credential or native gateway UI support is claimed.
- Claude through the product-compatible transport also passed: `scripts/check_live.py --model claude-haiku-4-5`; metadata context 200,000, measured usage 6,158 input / 184 output; no reasoning. Probe, real read, stream, replay, Stop and key scan all passed.

## Completed live desktop acceptance (2026-10-19)
- `npx tsx tests/phase2-live-desktop.ts` passes both gpt-4o-mini and
  claude-haiku-4-5 through the supplied base URL: actual add/probe/save/default,
  Home jailed README read, streamed output, measured token display, safeStorage
  restore after restart, identical persisted event replay and Home Stop.
- Latest desktop evidence: gpt-4o-mini metadata context 128,000, usage 14,405 input /
  233 output, Stop 90 ms; Claude metadata context 200,000, usage 6,194 input /
  132 output, Stop 332 ms. Neither emitted reasoning. Scanned 76 persisted
  files without plaintext credential; zero renderer errors. Sanitized evidence and
  screenshots are under ignored `artifacts/phase2-live/`.
- Native Anthropic adapter recheck passes with usage 6,779 input / 191 output,
  estimated fallback context 32,768, no thinking; probe/read/stream/replay/Stop
  and persisted-key scan pass. Product URL inference was not changed.
- Live providers can emit narration or fenced/multiline OpenUI; readable fallback
  is expected for invalid programs. The desktop checker accepts rendered KeyValue
  or readable output containing the real marker, and verifies recorded tool results
  independently. It handles multiple message blocks and locale token separators.
- Rechecked quality gates: 40 engine tests, 8 UI unit tests, ruff, strict mypy
  (48 files), TypeScript all pass. Production code/assets did not change in this
  validation follow-up; previous static/Electron/engine builds and desktop regression
  evidence remain applicable. Only the opt-in live test and evidence documents changed.
