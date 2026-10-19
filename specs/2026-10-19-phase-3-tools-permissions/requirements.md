# Phase 3: Tools and permission layer. Requirements

## Goal
The agent can read, create, edit and delete workspace files and run commands, all behind **one** permission
authority (`PermissionMiddleware`), with a command risk classifier, an undo path (snapshots), and a temporary
approval modal so `ask` works end to end before the Phase 4 inbox exists.

## In scope
- Filesystem tools: `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep` (deepagents
  `FilesystemMiddleware`), all jailed and permission-gated. Stock `execute` is excluded.
- Our `run_command`: PowerShell default, `cmd` fallback, 120 s default timeout, 200-line output cap with
  paging, Windows Job Object process-tree kill, scrubbed child environment.
- Atomic writes and per-mutation snapshots under `.harness/snapshots/` with a revert API.
- `PermissionMiddleware`: modes Read-only / Ask (default) / Auto; `.harness/rules.json` (tool × path glob →
  allow/ask/deny); deny → readable tool error; ask → LangGraph interrupt; always-ask list that survives Auto.
- Command risk classifier, table-driven.
- Temporary approval modal (approve / reject only).
- Branch chip switching via `git switch` behind the permission layer; **Worktree** option (`git worktree`
  under `.harness/worktrees/<task-id>`, creation is an approval).
- Workspace page (file tree with a system-files toggle, file viewer with agent-changed lines and a
  "waiting for approval" badge, the workspace's task list), `GET /files`.
- Two error states from `Errors.dc.html`: command timeout, jail block.

## Out of scope (later phases)
- Approvals **inbox**, edit-input-then-approve, allow-rule checkbox, durable resume of pending interrupts
  after an engine restart, Rules tab UI — Phase 4.
- Plan gate, deviation gate, activity timeline, thinking panel — Phase 6.
- Verify gate, test detection, `TerminalPanel`/`xterm`, `TestResults`, context ring — Phase 7.
- Skills, `web_search` tool, install flows — Phase 8. Phase 3 only reserves the `web_search` rule key.
- Full Settings > Permissions screen, remaining error cards (401/429/crash/fix-exhausted/no-tools),
  light theme — Phase 9.

## Functional requirements

### Jail and filesystem
- **R1** Every filesystem tool resolves the real path (symlinks and NTFS junctions) and rejects any target
  outside the workspace. `..`, absolute paths outside, UNC (`\\host\share`), drive-relative (`C:foo`),
  root-relative (`\foo`), alternate data streams (`a.txt:stream`) and reserved device names (`CON`, `NUL`,
  `COM1`) are rejected. Rejection returns a tool error the model can read; the run continues.
- **R2** `.harness/` is not reachable through any filesystem tool (no read, write, delete, glob or grep hit),
  and is not reachable through `run_command` path arguments that the classifier resolves inside it, except
  the specific engine-owned operations listed in R14/R16.
- **R3** Reads are capped (2 MB text, 2000 lines) and honour `offset`/`limit`; binary files return a clear
  error rather than mojibake.
- **R4** `write_file` and `edit_file` are **atomic**: content is written to a temp file in the same
  directory and moved into place with `os.replace`. A failure before the move leaves the original file
  byte-identical. `edit_file` requires a unique `old_string` unless `replace_all` is set, and reports the
  number of replacements.
- **R5** `delete` removes a single file only. Directories are refused with an error telling the model to use
  a command. Deleting a file that does not exist returns a normal error, not an exception.
- **R6** Every successful mutation (create, write, edit, delete, revert) first snapshots the previous state to
  `.harness/snapshots/<snapshot_id>/` with `meta.json` (`path`, `existed`, `ts`, `run_id`, `call_id`,
  `bytes`, `tool`). For a created file, `existed:false` and no content blob. Snapshot write failure aborts
  the mutation.
- **R7** `POST /snapshots/{snapshot_id}/revert` restores that file (or deletes it when `existed:false`) as an
  atomic write, records the revert as a new snapshot, and returns the restored path. Snapshots are pruned
  oldest-first beyond 200 entries or 20 MB, whichever is hit first; pruning never removes the snapshot a
  revert is currently using.

### Command execution
- **R8** `run_command` runs in the workspace root with PowerShell as the default shell and `cmd` as the
  fallback when PowerShell is unavailable. It returns exit code, duration, `truncated` flag and the last
  `offset`-paged window of output. Non-zero exits are normal results, not exceptions.
- **R9** Default timeout is 120 s. On expiry the **whole process tree** is killed (Windows Job Object,
  kill-on-close, children assigned before they run) and the tool returns a timeout error naming the elapsed
  limit. No descendant survives; a later check finds no orphan PID.
- **R10** A timeout above the default requires an approval even in Auto (the error card's "run with 300 s"
  action). Timeouts are capped at 600 s and rejected above that.
- **R11** Output is capped at 200 lines per result with a "N more lines" trailer and an `offset` parameter to
  page. A byte cap also applies so a single giant line cannot blow up the context.
- **R12** Child environments are built from an allowlist, never inherited wholesale. Registered secrets (the
  launch token and every provider key), `*_API_KEY`, `*_TOKEN`, `*_SECRET`, `OPENAI_*`, `ANTHROPIC_*`,
  `LANGSMITH_*` and `LANGCHAIN_TRACING*` are absent from every child process. A canary key placed in the
  parent environment never appears in child output, tool results, events or `events.jsonl`.
- **R13** `run_command` rejects a `cwd` that resolves outside the workspace and never executes a workspace
  file by direct path from a UI click.

### Permission layer
- **R14** `PermissionMiddleware` is the only authority. Every tool call — filesystem, `run_command`, and any
  future tool — is classified `allow`, `ask` or `deny` before it executes. `deny` returns a tool error the
  model can read and the run continues; `ask` raises a LangGraph interrupt with an approval payload and
  resumes with the user's decision; `allow` executes.
- **R15** Modes act as a ceiling: **Read-only** denies every mutation, command, delete and web call regardless
  of rules; **Ask** (default) applies rules with defaults reads=allow, writes=ask, delete=ask, commands=ask,
  web=ask; **Auto** applies rules with defaults writes=allow, delete=allow, commands=allow, reads=allow.
- **R16** Rules live in `.harness/rules.json` as `{tool: [{glob, action}]}` plus a `mode` default. Matching is
  by path glob for path tools and by tool name for `run_command`. The most specific matching rule wins
  (longest literal prefix, then fewest wildcards); an exact tie resolves to the most restrictive action
  (`deny` > `ask` > `allow`). A malformed or unreadable rules file fails **closed** (everything asks) and is
  reported, never silently ignored.
- **R17** These always ask, in every mode including Auto, unless an explicit `allow` rule exists for the exact
  tool+glob: any write to `.harness/rules.json`; any edit to any other `.harness/` path; a `web_search` query
  (no allow rule exists in Phase 3); any command the classifier marks high-risk.
- **R18** `GET /rules` returns the effective rules plus the mode; `PUT /rules` validates and writes them
  atomically. Changing the rules file is itself an approval when initiated by the agent, never when initiated
  by the user through the UI.

### Command risk classifier
- **R19** A table-driven classifier returns `{level: low|high, reasons[]}` for a command string. High-risk
  categories: recursive or forced delete, disk/format/partition operations, registry edits, encoded or
  base64 PowerShell, pipe-to-shell downloads, `git push --force`, `git reset --hard`, `git clean -fd`,
  package install/uninstall, network tools, and any path argument that resolves outside the workspace.
- **R20** The classifier sees through quoting, `&&`/`;`/`|` chains, PowerShell aliases (`ri`, `del`, `rm`,
  `gci | rm`), `-r`/`-recurse`/`-force`/`/s`/`/q` variants, case changes, and leading whitespace or `&`
  call operators. Each of these is a named test case; a false negative on any listed category fails the phase.

### Approvals (temporary UI)
- **R21** An `ask` decision emits `approval.requested` with a stable `approval_id`, the run id, kind
  (`tool`/`command`), tool name, resolved path or command text, risk level and reasons, and a short reason
  string. `approval.resolved` follows with the decision.
- **R22** `POST /runs/{run_id}/interrupts/{approval_id}` accepts `{decision: "approve"|"reject", reason?}`,
  resumes the graph, and returns 409 for an unknown or already-resolved approval. Rejecting never crashes the
  run: the model receives the rejection reason as the tool result and continues.
- **R23** A minimal modal renders a pending approval (tool, path or command in LTR monospace, risk badge,
  reason) with Approve and Reject. Keyboard: Enter approves, Esc rejects. It is a Radix dialog with focus
  containment and an accessible name; the run is visibly paused while it is open.

### Git
- **R24** The branch chip reads `.git/HEAD` without running a command (already true) and, on switch, calls the
  permission layer as a `git_switch` tool call, then runs `git switch <branch>`. Branch names are validated
  against git's ref rules and never passed as flags; `-`, `--` and shell metacharacters are rejected.
- **R25** A failed switch (dirty tree, unknown branch) returns the git stderr to the UI without changing the
  recorded branch, and does not corrupt `.git/HEAD`.
- **R26** The **Worktree** checkbox is enabled only for git repositories with `git` on `PATH`. When checked,
  the run's root becomes `.harness/worktrees/<task-id>` created with `git worktree add`, and creating it is an
  approval. The task record stores the worktree path; the user merges manually. If creation fails the run does
  not start and the error is shown.

### Workspace page and files API
- **R27** `GET /files?path=<rel>` returns, for a directory, entries with name, kind, size and a
  `changed` flag; for a file, its text content plus `changed_lines` (line ranges that differ from the newest
  snapshot of that path) and `pending_approval` (true when a pending approval targets that path).
- **R28** The Workspace screen matches `Workspace.dc.html`: header with folder icon, monospace name,
  `path · branch`, "باز کردن در اکسپلورر" and "کار جدید در این فضا"; three columns — files 260 px with a
  "فایل‌های سیستمی" toggle that reveals `.harness`, viewer flex with the "تغییر عامل · منتظر تأیید" badge and
  added lines highlighted in the `--ok` tint, tasks 280 px listing that workspace's tasks with status colour.
- **R29** Opening a workspace never executes a tool; the file viewer is read-only.

### Error states
- **R30** A command timeout renders the `Errors.dc.html` card: "دستور بعد از ۱۲۰ ثانیه متوقف شد", the note
  that the process and its children were killed, the command preview, and the actions "اجرا با مهلت ۳۰۰ ثانیه"
  (raises a new approval) and "رد".
- **R31** A jail block renders the jail card: "دسترسی مسدود شد", the resolved offending path in LTR monospace,
  and copy stating the access is never allowed, **even with approval**. The message returned to the model says
  the same thing; the run continues.

## Non-functional
- Quality gates green: `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit`.
- Security tests are mandatory and must be real tests, not skips: junction/symlink escape, `..`, UNC, env
  scrubbing, rules-file protection in Auto, classifier table.
- No secrets in code, logs, events, fixtures or snapshots. Snapshots may contain user file content and live
  under `.harness/`, which is already excluded from events and from the agent.
- Small modules: `tools/jail.py`, `tools/fs.py`, `tools/command.py`, `tools/snapshot.py`,
  `permissions/rules.py`, `permissions/classifier.py`, `permissions/middleware.py`. No business logic in React
  components.

## Decisions
- **Interrupt placement.** `interrupt()` is raised from `PermissionMiddleware.aafter_model`, not from inside
  `awrap_tool_call`. Verified against the installed `HumanInTheLoopMiddleware` (langchain 1.4.6), which raises
  its interrupt in `after_model`/`aafter_model` and applies the decision in `wrap_tool_call`/`awrap_tool_call`.
  This keeps
  resume semantics identical to the stock path while our rules stay dynamic. We do **not** use
  `interrupt_on` because it cannot express path- and command-aware policy.
- **Delete is a first-class tool.** deepagents 0.7.28 exposes `delete` in `FsToolName`; using it gives deletion
  its own rule key instead of hiding it inside `run_command`.
- **PowerShell first.** Phase 0 proved stock `LocalShellBackend` leaves a 20 s descendant alive after a 1 s
  timeout and returns ~4.1 s late. Our own tool with a Job Object replaces it.
- **Snapshots double as the diff source.** `changed_lines` for the viewer is computed against the newest
  snapshot, so no separate change-tracking store is needed.
- **Phase 3 approvals are in-memory.** Pending interrupts do not survive an engine restart; the task is marked
  interrupted and Phase 4 adds durable resume.
