# Phase 3: Tools and permission layer. Plan

Status: **Draft for approval (Step A).** Do not write product code until the user replies "approved".
Implement top to bottom, one commit per completed step.

## Step 1: Verify contracts, define the data
- Inspect the installed deepagents 0.7.28 `FilesystemMiddleware` (`tools=` list, `delete` signature, backend
  protocol methods), langchain 1.4.6 middleware hooks (`after_model`/`awrap_tool_call` ordering and resume),
  LangGraph 1.2.16 `interrupt`/`Command(resume=...)`, pywin32 312 Job Object calls, and `os.replace` semantics
  on Windows. Record exact signatures and versions in `learnings.md`; no guessing, no invented API shapes.
- Define typed schemas before consumers: `Rule`, `RulesFile`, `Mode`, `Decision`, `RiskLevel`, `ApprovalRequest`,
  `ApprovalDecision`, `CommandResult`, `FileEntry`, `FileContent`, `SnapshotMeta`. Promote `approval.requested`
  and `approval.resolved` from `FutureEvent` to real discriminated events with those payloads, and extend
  `RunRequest` with `worktree: bool = false`. Regenerate the TypeScript protocol.
- Add route contracts: `GET /files`, `GET /rules`, `PUT /rules`, `POST /runs/{id}/interrupts/{iid}`,
  `POST /snapshots/{id}/revert`, `POST /workspaces/branch`. Update CORS only for methods actually needed.
- Tests: schema round-trip, discriminated-union generation, `RunRequest` default compatibility (an old payload
  still parses). If a verified signature contradicts this spec, revise the spec first. (R14, R18, R21–R22, R27)

## Step 2: Harden the jail and build the filesystem tools
- Split `contained()` into a reusable resolver that returns the resolved path plus the workspace-relative form,
  keeps the existing UNC/ADS/device/`..`/`.harness` rejections, and adds a post-`resolve()` containment check
  for every intermediate directory so a junction created mid-path cannot escape.
- Replace `ReadOnlyBackend` with `WorkspaceBackend`: `read` (2 MB/2000-line caps, binary detection), `write`
  and `edit` (atomic temp+`os.replace`), `delete` (single file only), plus `ls`/`glob`/`grep` filtering out
  `.harness`. Keep the virtual `/path` prefix handling.
- Wire `FilesystemMiddleware(tools=["ls","read_file","write_file","edit_file","delete","glob","grep"])` and
  drop the Phase 1 `ReadOnlyTools` allowlist.
- Tests: real symlink and junction escape (created, not mocked), `..`, absolute outside, UNC, drive-relative,
  ADS, device names, `.harness` via every tool, atomic write rollback (patched failure), edit uniqueness,
  delete-directory refusal, binary read. (R1–R5)

## Step 3: Snapshots and revert
- `tools/snapshot.py`: create a snapshot before each mutation, write `meta.json`, prune beyond 200 entries /
  20 MB, and revert atomically (recording the revert itself as a snapshot).
- Call it from the backend's write/edit/delete paths so no mutation can bypass it, and from revert.
- Expose `POST /snapshots/{id}/revert` and `changed_lines` computation (diff newest snapshot vs current) for R27.
- Tests: create/write/edit/delete each snapshot the previous state, revert restores bytes, revert of a created
  file deletes it, revert is itself reversible, prune keeps the newest and never breaks an in-flight revert,
  snapshot failure aborts the mutation. (R6–R7)

## Step 4: `run_command` with real process-tree kill
- `tools/command.py`: PowerShell default (`-NoProfile -NonInteractive -Command`), `cmd` fallback (`/d /s /c`)
  when PowerShell is absent; workspace cwd; 120 s default, 600 s cap; 200-line + byte cap with `offset` paging;
  exit code and duration in the result.
- Windows Job Object: create the process suspended, assign to a kill-on-close job, resume, then
  `TerminateJobObject` on timeout/cancel. Non-Windows path uses a process group and is exercised only by a
  skip-marked test so Linux/macOS stay unblocked.
- Child environment: allowlist builder that drops registered secrets, `*_API_KEY`, `*_TOKEN`, `*_SECRET`,
  `OPENAI_*`, `ANTHROPIC_*`, `LANGSMITH_*`, `LANGCHAIN_TRACING*`; no inherited tracing.
- Tests: timeout kills the tree (assert the grandchild PID is gone with psutil, no orphan), 120 s default,
  paging/truncation, non-zero exit, cwd outside rejected, env scrubbing with a canary key, PowerShell and cmd
  both run a real command. (R8–R13)

## Step 5: Rules engine and risk classifier
- `permissions/rules.py`: load/validate `.harness/rules.json`, fail closed on malformed input, specificity
  ordering (longest literal prefix, then fewest wildcards, then deny > ask > allow), mode ceiling, and the
  always-ask list from R17. Path matching uses the resolved workspace-relative path, case-insensitive on
  Windows.
- `permissions/classifier.py`: table-driven high-risk categories from R19, with a normalizer that strips
  quotes, splits `&&`/`;`/`|` chains, lowercases, expands PowerShell aliases, and resolves path arguments.
- Tests: a parameterized table covering every category and every tricky form in R20 (quoting, chains, aliases,
  case, `-r`/`-force`/`/s`/`/q`), specificity ordering, tie-breaking, fail-closed, `.harness/rules.json`
  protection in Auto, `web_search` still asking in Auto. (R16–R17, R19–R20)

## Step 6: `PermissionMiddleware`
- `permissions/middleware.py`: in `aafter_model`, resolve a decision for each pending tool call; on `ask`,
  emit `approval.requested` and `interrupt()`; on `deny`, leave a marker so the wrapper returns an error. In
  `awrap_tool_call`, execute `allow`/approved calls, return the readable error for `deny`/rejected calls, and
  feed the rejection reason back as the tool result.
- Wire it into `build_agent` next to `TodoListMiddleware` and `FilesystemMiddleware`; register `run_command` in
  `tools=[...]` and keep stock `execute` excluded.
- `RunManager` tracks pending approvals per run, resolves them via `Command(resume=...)`, emits
  `approval.resolved`, and returns 409 for unknown/resolved ids. Rejecting must not raise.
- Tests: allow executes, deny returns an error and the run continues, ask interrupts and resumes with approve,
  ask + reject continues with the reason, 409 paths, Auto still asks for `.harness` writes and high-risk
  commands, Read-only denies everything mutating. (R14–R15, R21–R22)

## Step 7: Git — branch switch and worktree
- Validate branch names against git ref rules; run `git switch <branch>` through the permission layer as a
  `git_switch` call; return stderr on failure without touching recorded metadata.
- `POST /workspaces/branch` for the chip. Worktree: detect git repo + `git` on PATH, create
  `.harness/worktrees/<task-id>` via `git worktree add` behind a `worktree_create` approval, run with that root,
  record the path on the task.
- Tests: valid/invalid branch names, flag injection (`-`, `--force`), dirty-tree failure keeps HEAD, worktree
  creation requires approval, run root is the worktree, non-git workspace disables the option. (R24–R26)

## Step 8: Workspace page and approval modal
- `GET /files?path=` per R27. Workspace screen rebuilt from `Workspace.dc.html` with tokens, Tailwind v4,
  Radix and Phosphor: header, three columns, system-files toggle, changed-line highlighting, waiting badge,
  task list. Route via query param so static export keeps working.
- Approval modal per R23 (Radix dialog, backdrop `rgba(0,0,0,0.62)`, radius 28 px, Enter/Esc, focus containment,
  paused-run affordance). Wire the Home branch chip dropdown and the Worktree checkbox to their new routes.
- Tests: UI unit tests for the reducer/API client (approval state, changed lines, tree toggle) and a desktop
  test through real preload for open workspace → view file → trigger approval → approve → run completes. (R23,
  R27–R29)

## Step 9: Error states
- Command-timeout card and jail-block card from `Errors.dc.html`, exact Persian strings, with the 300 s re-run
  approval action and the "never allowed, even with approval" copy.
- Map engine errors to these cards: timeout result, jail rejection result, so the UI distinguishes them from a
  generic failure.
- Tests: timeout result renders the timeout card with the 300 s action and the action raises a new approval;
  jail rejection renders the jail card and the model-facing message matches. (R30–R31)

## Step 10: Validate and hand off
- Run every automated and manual item in `validation.md`; attach real test names and screenshot references.
- Write `learnings.md` (verified APIs/versions, deviations, surprises, every deferred TODO, known limitations).
- Propose the roadmap edit in `roadmap-proposal.md` and wait for approval before touching `roadmap.md`.
