# Phase 6 implementation evidence

Implementation is in progress. Unchecked validation items are not completion claims.

## Step 1: installed runtime contracts

- Inspected installed deepagents 0.7.28 `graph.py`, `middleware/subagents.py`, `middleware/summarization.py`, LangChain 1.4.6 `agents/middleware/todo.py`, and existing SQLite/mixed-interrupt tests. No package or API upgrade.
- `TodoListMiddleware` injects `write_todos` with `{content, status}` items; statuses are pending/in_progress/completed. It has neither stable IDs nor failed. The adapter will encode an accepted ID in the content prefix `[step_id] title`; failed is an engine-owned lifecycle outcome, not a fabricated stock enum. Structural todo edits must become plan proposals rather than replace accepted state.
- The factory injects a default general-purpose child unless overridden. Merely supplying reviewer/researcher specs does not remove it. Supplying a replacement `SubAgentMiddleware` with compiled child graphs replaces that slot by middleware name. Child graphs can be built with `create_agent`, only explicit safe-read tools and an independent default-deny tool wrapper. They need no nested factory, inherited parent tools, skills or write-capable harness defaults.
- `test_real_parallel_compiled_children_and_namespaces` uses the real factory, two compiled children and SQLite. A rendezvous tool requires both child tool handlers to run before either can return, proving actual concurrency. Two distinct child namespaces stream and both result tool IDs survive the final parent checkpoint.
- `ReadOnlyDelegateMiddleware` is an independent allowlist ceiling (ls/read_file/glob/grep). `test_delegate_ceiling_denies_even_registered_tools` proves registered mutation/command/task/settings/unknown tools cannot reach their handlers. Production child backend still must enforce the existing workspace jail; this proof does not claim OS isolation.
- Installed summarization runs in `awrap_model_call`, returns an `ExtendedModelResponse` with a `Command` updating `_summarization_event`, `_summarization_session_id` and possibly messages. `_summarization_event` contains cutoff_index/summary_message/file_path. It changes effective model input, retaining raw history. Its separate summary call bypasses ordinary model middleware: production instrumentation must supply a redacting summarizer and sanitize the command update, not just `response.result`.
- `test_real_summarizer_persists_transition_not_prose` lowers only its test trigger to four messages, retains two, invokes the installed summarizer and verifies the real private state, source tag, offload path and preserved raw messages. A public notice must derive from that durable transition, not a response string.

## Contract bounds and semantics

- Plans: 1–64 steps, unique ASCII IDs of 1–64 letters/digits/underscore/hyphen; titles trimmed 1–240 chars; up to 64 declared patterns per step, each 1–512 chars; verify command trimmed 1–4000 chars. Patterns use workspace-relative POSIX separators; absolute/drive/ADS/traversal/control forms are refused. Accepted records/progress are engine-owned, excluded from submission input.
- Settings: strict integer step threshold 1–64 (review at >=); file threshold 1–10000 (review at >); strict boolean deviation flag. Defaults 4/3/true. Fixed high-risk trigger is separate.
- Activity scope records have stable scope/parent/turn/step identity and agent/model attribution. Existing message/reasoning/tool events gain optional scope; unscoped old events remain valid. Plan/activity/delegate/summary/context/steering events are typed, generated from Python. Future `ui.render`/`test.result` stay reserved.
- Timings are persisted UTC event timestamps, including waits/downtime. Latest-request context occupancy is separate from cumulative usage. Affected summary message count may be unavailable; no invented count.
- Steering submission: client ID 1–64 safe characters, trimmed text 1–32000 chars, ordered run-owned queued/delivered/cancelled acknowledgement. Planned HTTP contract: authenticated POST `/runs/{id}/messages`; unknown run 404, terminal/conflicting duplicate 409, malformed input 422; identical duplicate returns the existing acknowledgement. Delivery belongs in a parent-only before-model state update with deterministic HumanMessage IDs, then durable checkpoint reconciliation. Never invoke a second graph or release the pre-tool mixed barrier.

## Evidence so far

- Full backend suite after the new planning contracts and mixed plan/question SQLite proof: **340 passed in 171.04 s**. Ruff passed.
- Strict mypy: 99 source files passed. UI unit tests: 37 passed. Generated protocol and TypeScript check passed.
- Full phase safety/runtime/UI/Windows validation remains pending. Steps 2–6 and final roadmap approval remain pending.
