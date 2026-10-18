# Phase 0 spike evidence

Implementation experiments and technical validation pass. After the user enabled Developer Mode, the real symlink test passed and the full Python suite passed all 25 tests. Constitution amendments and the roadmap update still await approval. Do not start Phase 1 yet.

## Environment
- Windows 10 x64 build 19045, repository `E:\Agentic\Harness`.
- uv selected managed CPython 3.12.14 (system default is 3.10.5; do not use it).
- Node 24.18.0, npm 11.16.0, uv 0.12.19, Git 2.46.0.windows.1.
- Initialized local Git because the supplied folder was not a repository. No remote configured.
- Exact dependency resolution: `spikes/python/uv.lock`, `spikes/ui/package-lock.json`.

| Area | Verified installed versions |
|---|---|
| Agent | deepagents 0.7.28, langchain 1.4.6, langchain-core 1.6.12, langgraph 1.2.16 |
| Providers | langchain-openai 1.7.2, langchain-anthropic 1.7.6, openai 3.35.1, anthropic 1.15.0 |
| Sidecar | FastAPI 0.146.0, uvicorn 0.54.0, PyInstaller 6.22.3, pywin32 312, psutil 7.2.2 |
| UI | Next.js 16.4.2, React/React DOM 19.3.1, Electron 44.9.0 |
| OpenUI | react-lang 1.0.1, react-ui 0.18.1, Zod 4.6.7 |
| Checks | ruff 0.17.1, mypy 2.4.0, pytest 9.1.1, TypeScript 7.0.2, Playwright 1.64.1 |

`test_locked_environment` compares installed Python distributions and direct npm dependencies to the locks. uv's universal lock includes alternate-platform packages that are intentionally absent on Windows.

## Verification sources
- Installed package source and declarations are authoritative for these pinned experiments.
- [deepagents distribution](https://pypi.org/project/deepagents/).
- [OpenUI React API](https://www.openui.com/docs/api-reference/react-lang): component definitions, library prompt, renderer and structured errors.
- [Next static export](https://nextjs.org/docs/app/guides/static-exports).
- [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects): process membership and kill-on-close lifetime.

## Reproduction and evidence

Run the ordered commands in `spikes/README.md`. Runtime experiments use no real model keys or live provider calls. Dependency installation and Electron's first binary download require network access. Generated evidence lives in ignored `spikes/artifacts/`; tests regenerate it. Installed source examined: `deepagents/graph.py`, `deepagents/backends/local_shell.py`, provider `chat_models` modules, and OpenUI `dist/*.d.mts` declarations.

## OpenUI and static export — supported

Both `file://` and privileged standard/secure `app://` load the exported HTML, scripts, and CSS without a Next server. Recommend `app://` for a consistent origin and explicit resource routing. `assetPrefix: "."` supports both root-page loading paths. No product screen is implemented.

Verified API: `defineComponent({name, description, props: z.object(...), component})`, using `z` from `zod/v4`. Component renderers receive `{props, renderNode}`; nested schemas use `Component.ref`. `createLibrary({components, root})` returns the library, and `library.prompt({additionalRules, examples})` generates the model prompt. The stylesheet export is `@openuidev/react-ui/index.css`, not `styles.css`.

```tsx
<Renderer response={text} library={library} isStreaming={streaming} onError={onError} />
// Complete definitions: spikes/ui/app/library.tsx
// Tested program: root = Stack([Callout("Hello"), KeyValue("State", "Ready")]);
```

The Electron test delivers incomplete string prefixes, checks partial text, then final nested `Callout` and `KeyValue` output. Malformed unknown-component input falls back to readable text. Ignore transient streaming parse errors and warning-only errors; fatal completed-output errors trigger fallback. A stable callback consults current response/stream state to avoid stale error callbacks.

An initial screenshot exposed a test false positive: components existed briefly before raw fallback replaced them. Tests now wait for hydration and two animation frames after completion, then assert final cards remain and fallback is absent. Corrected final screenshots were visually inspected. Tests also check CSS loading, failed asset requests, and renderer exceptions. Evidence: `openui.json`, `openui-{file,app}.png`, `openui-{file,app}-fallback.png`.

## Packaged sidecar and Windows lifetime — supported

`build.ps1` packages both `sidecar.exe` and `job_launcher.exe` as onedir applications. Electron launches the watchdog, which creates the engine suspended, assigns it to a kill-on-close Windows Job Object, then resumes it. The job handle is not inherited; descendants inherit job membership. The watchdog waits for EOF on its Electron-owned input pipe. Normal quit closes it; force-killing Electron also closes it at the OS level. Job closure kills the engine and its fixture descendant. No installed Python interpreter is needed for this launch path.

The engine binds a real socket with `bind(("127.0.0.1", 0))`, prints `{"port": N}` as its first stdout line, and gives that same socket to uvicorn. There is no free-port probe/rebind race. The Electron launcher verifies the first engine line; Electron itself can emit a blank line on its own stdout. Health returns 401/401/200 for missing/wrong/correct bearer authentication.

Windows Electron stdin closed immediately in the original harness. The test now supplies an ephemeral `SPIKE_TOKEN` environment value; Electron removes it before child creation, then uses private stdin pipes for watchdog and engine. Product Electron should generate its own token. Child environments are allowlisted, and tests check token absence from child environments, arguments, stdout/stderr, and generated artifacts. No token enters URLs or fixture files.

Normal shutdown uses a test-only authenticated `POST /quit` route: engine control output asks Electron to call `app.quit()`. Force-kill tests kill only Electron main before observing cleanup. All lifecycle assertions precede emergency test cleanup. A startup-failure test covers a missing executable.

Sample cleanup measurements: 1.047 seconds normal, 0.063 seconds forced; both below the five-second bound. `sidecar-normal.json` and `sidecar-force.json` record regenerated timings, ports, PID observations, binding/auth results, and environment checks without secrets. No owned Electron processes remained after testing.

`types-pywin32` incorrectly declares `CreateJobObject` as returning `None`. A narrow callable cast records that mismatch; runtime handle behavior is tested. Assignment failures terminate the suspended process instead of leaving it unowned.

## deepagents APIs and demo model — supported with explicit planning middleware

Confirmed factory parameters: `model`, `tools`, `system_prompt`, `middleware`, `subagents`, `skills`, `memory`, `permissions`, `backend`, `interrupt_on`, `response_format`, `state_schema`, `context_schema`, `checkpointer`, `store`, `debug`, `name`, `cache`.

```python
agent = create_deep_agent(
    model=demo, tools=[echo], system_prompt="SPIKE_AUTHORED_PROMPT",
    backend=FilesystemBackend(root_dir=fixture, virtual_mode=True),
    skills=["/skills/"], memory=["/memory.md"],
    middleware=[TodoListMiddleware()], checkpointer=InMemorySaver(),
    subagents=[{"name": "reviewer", "description": "Inspect fixtures",
                "model": reviewer, "system_prompt": "Inspect only", "tools": []}],
)
```

The model-neutral default configuration did **not** expose `write_todos`. Passing LangChain's `TodoListMiddleware` explicitly makes it available independently of model-specific profiles. This is a verified spike workaround; constitution adoption is still proposed. Captured model messages contain the caller's authored prompt and fixture memory/skills metadata, without the legacy authored base prompt. Enabled middleware still appends tool/memory/skills instructions.

With `stream_mode=["messages", "updates"]`, `subgraphs=True`, v1 items are `(namespace, mode, payload)`. Message payloads contain a chunk and metadata including `langgraph_node`; updates map node names to state changes. Todos produce model calls, a `tools` update, and `TodoListMiddleware.after_model`. Delegated model activity appears beneath a `tools:<id>` namespace; the parent `task` result completes the delegate. CodeHarness must map this to its own typed events; the library does not emit CodeHarness `subagent.started` objects. Actual summaries are in `agent-stream.json`.

`demo.py` subclasses `BaseChatModel` with `bind_tools`, `_generate`, and `_stream`; it emits `AIMessageChunk` text and `tool_call_chunks`. A real deepagents run consumes scripted todos, delegation, echo result, and a final response. Its test forbids network connections.

Interrupt values contain `action_requests` and `review_configs`: tool name, arguments, description, and allowed decisions. This version allows `approve`, `edit`, `reject`, and `respond`; the app may expose its specified subset. Verified resume payloads:

```python
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)
agent.invoke(Command(resume={"decisions": [
    {"type": "reject", "message": "Human declined"}
]}), config)
```

Both reuse the thread ID and in-memory checkpointer; rejection becomes a tool result and the model finishes. Actual requests are in `interrupt-{approve,reject}.json`. Full runnable examples and effective-prompt assertions: `tests/test_agent.py`.

## Stock Windows shell — unsuitable for product safety

Verified constructor: `LocalShellBackend(root_dir=..., virtual_mode=True, timeout=..., env=..., inherit_env=False)`. It uses `subprocess.run(shell=True)`; Windows runs cmd, with PowerShell invoked explicitly. Output and nonzero exits work for both. Virtual filesystem mode does not constrain shell access.

Both one-second timeout tests return exit code 124 but leave a twenty-second descendant alive. Recorded command durations were 4.156 seconds under cmd and 4.328 seconds under PowerShell. The tests kill the fixture after observing it. This is a passing characterization of **unsafe stock behavior**, not a passing process-tree safety guarantee. Evidence: `shell-cmd.json`, `shell-powershell.json`.

The existing constitution permits a custom command tool. Phase 3 must implement it behind permissions, exclude stock `execute`, and enforce actual job lifetime/deadlines. The sidecar job experiment provides a mechanism to evaluate, not production permission code.

## Reasoning transport — adapter behavior verified

Six tests send synthetic responses through real SDK HTTP clients and installed adapters. These provider SDK pins use `httpx2`; sidecar health tests use independent `httpx`. No live endpoint compatibility is claimed.

- Generic `ChatOpenAI(use_responses_api=False)` discards DeepSeek-style `reasoning_content` in full responses and streamed deltas. It does not survive as additional fields or normalized reasoning. Phase 2 needs a tested provider-aware adapter/converter to preserve it.
- Native Anthropic thinking survives as structured raw content (`type: "thinking"`, `thinking`) and normalized `content_blocks` (`type: "reasoning"`). Streamed `thinking_delta` is preserved.
- Ordinary answer text is never classified as reasoning; absent thinking yields no reasoning blocks. Report that absence honestly.

Anthropic's private client slot is injected with a real SDK using mocked transport solely for the experiment; do not copy that private injection into production. Exact fixtures: `tests/test_reasoning.py`.

Early runs inherited host LangSmith tracing settings and attempted telemetry for synthetic data. The test bootstrap now removes host API-key/tracing entries and disables tracing before test-module imports. Subsequent agent/provider runs pass without those attempts. Product environment isolation must also be explicit. No real credentials were added to source, fixtures, or workspace files.

## Windows containment — verified for the spike matrix

All nine containment checks pass: internal/new targets, case/separator variants, traversal, outside absolute paths, sibling-prefix collisions, drive-relative and UNC/root-relative rejection, and real symlink/junction escapes. Both link checks reject existing content and missing files under their outside targets. No network share is contacted.

The symlink fixture initially failed at creation with `WinError 1314`. After the user enabled Developer Mode, `uv run pytest tests/test_containment.py -v` passed all nine checks, including real symlink creation and escape rejection. No skip, mock, or containment-code workaround was used.

Initial diagnosis: the session was not elevated and its process token did not
contain `SeCreateSymbolicLinkPrivilege`. A direct `CreateSymbolicLinkW` probe with
flags `0x1 | 0x2` (directory plus allow-unprivileged creation) also returned 1314,
independently of Python's `Path.symlink_to()`. The probe uses a disposable local
directory and removes its fixtures. This establishes an OS prerequisite failure,
not a failure of the containment check. The test now reports the required Windows
setup explicitly if that prerequisite is absent. Developer Mode resolved this prerequisite without a containment-code change. Microsoft documents that the
[unprivileged creation flag requires Developer Mode](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createsymboliclinkw).

`containment.py` resolves paths and checks `is_relative_to()`, explicitly rejecting ambiguous path forms first. Temporary links are removed directly, never by recursively traversing their targets. This candidate is not race resistant: a reparse point can change between resolution and access. Phase 3 needs operation-boundary checks plus alias/device/reparse/root/protected-path review; this experiment establishes neither shell isolation nor a sandbox.

## Proposed constitution changes
Concrete proposed text is in `proposed-constitution-changes.md`: explicit todo middleware, verified stock-shell fallback, reasoning preservation limits, sidecar/token/tracing isolation, and the Phase 0 roadmap/handoff entry. No constitution file has been edited.

## Outstanding work
- ruff and strict mypy pass (11 Python source files); TypeScript, Next static export, and Electron launcher builds pass.
- Both Electron protocol/stream/fallback tests pass; corrected final-card screenshots were inspected.
- Latest complete pytest run: **25 passed in 18.34 seconds**, with no skipped tests. Ruff and strict mypy also passed on this rerun.
- Remaining: approve/apply constitution amendments and finish the roadmap update. Technical validation is green; approval remains pending.
- Phase 1 handoff: pinned APIs, explicit todo middleware, app protocol, packaged job/watchdog lifetime, scripted demo, stream/interrupt mapping, reasoning limits, and the verified spike containment matrix with its documented limitations. All code is isolated under `spikes/`.
