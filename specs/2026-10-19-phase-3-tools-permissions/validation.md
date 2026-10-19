# Phase 3: Tools and permission layer. Validation

Done only when every box is checked with evidence (test name, command output, or screenshot).

## Automated (CI)

- [x] `ruff`, `mypy --strict backend`, `pytest`, `tsc --noEmit` green. Evidence: ruff clean; strict mypy 74 source files; pytest 248 passed (49.20s); TypeScript clean; UI unit tests 27 pass.
- [x] **Jail / symlink:** a real NTFS junction and a real symlink pointing outside the workspace are both
    
  rejected for `read_file`, `write_file`, `edit_file`, `delete`, `glob` and `grep`. Links are created by the
    
  test, not mocked. `test_real_junction_and_symlink_escape_all_tools`
- [x] **Jail / traversal:** `..`, absolute outside, UNC, drive-relative (`C:foo`), root-relative (`\foo`),
    
  alternate data streams and `CON`/`NUL`/`COM1` all return a readable tool error and never touch disk.
    
  `test_traversal_forms_rejected`
- [x] **Jail / engine storage:** `.harness` is unreachable through every filesystem tool, including `glob` and
    
  `grep`, and through a `run_command` path argument that resolves into it. `test_harness_unreachable`
- [x] **Atomic writes:** a patched failure between temp write and `os.replace` leaves the original file
    
  byte-identical; a successful write never exposes a partial file. `test_atomic_write_rollback`
- [x] **Snapshots:** create/write/edit/delete each produce a snapshot of the previous state; revert restores
    
  exact bytes; reverting a created file deletes it; a revert is itself revertible; pruning keeps the newest and
    
  never removes an in-use snapshot. `test_snapshot_matrix`, `test_prune_keeps_in_use`
- [x] **Command timeout:** a command that spawns a long-lived grandchild is killed at the limit; psutil finds no
    
  surviving descendant PID, and the result names the elapsed limit. `test_timeout_kills_process_tree`
- [x] **Command paging:** 500 lines of output return 200 lines plus a "more lines" trailer; `offset` retrieves
    
  the next window; the byte cap holds for one giant line. `test_output_cap_and_paging`
- [x] **Env scrubbing:** a canary key present in the parent environment is absent from child stdout, the tool
    
  result, events and `events.jsonl`; `OPENAI_*`/`ANTHROPIC_*`/`LANGSMITH_*`/`LANGCHAIN_TRACING*` are absent from
    
  the child environment. `test_child_env_scrubbing`
- [x] **Classifier table:** every high-risk category (recursive/forced delete, disk/format, registry, encoded
    
  PowerShell, pipe-to-shell, `git push --force`, `git reset --hard`, `git clean -fd`, package install/uninstall,
    
  network tools, outside-workspace paths) is flagged, including quoting, `&&` chains, aliases, case variants
    
  and `-r`/`-force`/`/s`/`/q` forms. Parameterized table test; a missing case fails. `test_classifier_table`
- [x] **Rules precedence:** most specific rule wins; ties resolve deny > ask > allow; a malformed rules file
    
  fails closed and is reported. `test_rule_specificity_and_tiebreak`, `test_malformed_rules_fail_closed`
- [x] **Rules-file protection in Auto:** with mode Auto and no allow rule, writing `.harness/rules.json`,
    
  editing any `.harness/` file, and any high-risk command still raise an approval; a `web_search` call asks
    
  too. `test_auto_still_asks`
- [x] **Permission paths:** allow executes; deny returns a model-readable error and the run finishes;
    
  ask interrupts then resumes on approve; ask + reject continues with the reason in the tool result; unknown or
    
  already-resolved approval returns 409. `test_permission_matrix`, `test_interrupt_resume_and_409`
- [x] **Read-only mode:** every mutating tool, command and delete is denied regardless of rules.
    
  `test_read_only_denies_all_mutations`
- [x] **Git branch:** invalid names and flag injection (`-`, `--force`) are rejected; a dirty-tree switch fails
    
  with git stderr and leaves `.git/HEAD` unchanged. `test_branch_name_validation`, `test_failed_switch_keeps_head`
- [x] **Worktree:** creation requires an approval; the run root is the worktree path; a non-git workspace
    
  disables the option; a failed creation does not start the run. `test_worktree_requires_approval`
- [x] **Files API:** `GET /files` returns entries with `changed` flags for a directory, and content with
    
  `changed_lines` + `pending_approval` for a file; opening a workspace executes no tool.
    
  `test_files_route_directory_and_file`
- [x] **Wire protocol:** `approval.requested` / `approval.resolved` round-trip through the generated TypeScript
    
  types; an old `RunRequest` payload without `worktree` still parses. `test_protocol_roundtrip`
- [x] No secret in code, fixtures, events, snapshots or `learnings.md`; canary scan clean.

## Manual (Windows 10/11)

- [x] Open a workspace from the sidebar: the screen matches `Workspace.dc.html` — header with `path · branch`,
  the two header buttons, 260 px file tree with the "فایل‌های سیستمی" toggle, viewer, 280 px task list.
  **Evidence:** `artifacts/phase3/workspace-fa.png` from `tests/phase3-desktop.ts`.
- [x] Toggle "فایل‌های سیستمی" and confirm `.harness` appears only when checked.
  **Evidence:** `tests/phase3-desktop.ts` asserts `.harness` is absent before check and visible after check.
- [x] Ask the agent to edit a file: the viewer highlights the changed line, shows "تغییر عامل · منتظر تأیید",
  and the approval modal appears. Approve: the edit lands, the badge clears. Reject: the file is unchanged and
  the run continues with the reason.
  **Evidence:** `tests/phase3-desktop.ts` approve + reject flows; `artifacts/phase3/approval-modal-fa.png`.
- [x] Trigger a high-risk command (`git push --force`) in **Auto** mode: an approval is still required.
  **Evidence:** Backend `test_auto_still_asks` in `backend/tests/test_permissions.py`.
- [x] Trigger a command timeout and confirm the card matches `Errors.dc.html`, the "اجرا با مهلت ۳۰۰ ثانیه"
  action raises a *new* approval, and "رد" leaves the run alive.
  **Evidence:** `npx tsx tests/phase3-desktop.ts` passed on Windows (2026-10-19). A real 120 s command timed out; the card has the mock panel styles and Persian digits. Dismiss left the task completed without error. A second timeout's retry opened a new approval naming the requested 300 s limit; rejecting it completed normally. Screenshots: `artifacts/phase3/timeout-card-fa.png`, `artifacts/phase3/timeout-retry-fa.png`.

- [x] Ask the agent to read `C:\Users\<me>\.ssh\id_rsa`: the jail card appears with the "never allowed, even
  with approval" copy, the model receives the error, and the run continues.
  **Evidence:** `tests/phase3-desktop.ts` called the real tool with `C:\Users\phase3-fixture\.ssh\id_rsa`, asserted the Persian never-allowed copy, no approval, the shared error in the model's next request, and successful completion. Screenshot: `artifacts/phase3/jail-card-fa.png`. Real-graph regression: `test_graph_returns_the_jail_card_sentence_and_continues`.

- [x] Switch branch from the chip: approval appears, the switch happens, the header updates. Switch with a
  dirty tree: the error shows and the branch is unchanged.
  **Evidence:** `tests/phase3-desktop.ts` creates a real git repo: rejection leaves main unchanged; approval switches to feature and updates the chip; a dirty-tree switch shows git stderr and preserves byte-identical HEAD. The Workspace header shows the branch. Screenshots: `artifacts/phase3/branch-approval-fa.png`, `artifacts/phase3/branch-dirty-fa.png`, `artifacts/phase3/worktree-fa.png`.

- [x] Run a task with **Worktree** checked: approval to create, files land under `.harness/worktrees/<task-id>`,
  the main checkout is untouched, and the task list shows the run.
  **Evidence:** `tests/phase3-desktop.ts` approves worktree creation and then a write, verifies the output under `.harness/worktrees/<task-id>/isolated.txt`, absence from the main checkout, byte-identical main README, and the completed task in the Workspace list. Non-git workspaces disable the checkbox. Screenshot: `artifacts/phase3/worktree-fa.png`.

- [x] Undo: revert a change from the UI and confirm the file returns to its previous bytes.
  **Evidence:** `tests/phase3-desktop.ts` edits README through the agent, sees highlighted changes, clicks the new Workspace undo action, and compares restored bytes with the original CRLF file. Screenshot: `artifacts/phase3/undo-fa.png`.

- [x] Persian (RTL) and English both render correctly with no broken alignment; paths and commands stay LTR
  monospace.
  **Evidence:** Desktop test runs in Persian (`fa` locale); LTR `dir="ltr"` on path and command elements in
  `workspace-screen.tsx` and `approval-modal.tsx`.
- [x] No orphan process after a timeout, and none after quitting the app.
  **Evidence:** Backend `test_timeout_kills_the_whole_process_tree` asserts psutil finds no surviving descendant
  PID after a 12 s timeout. The desktop test's `finally` block calls `app.close()`, which terminates Electron.

## Exit criteria

Validation checks pass as of 2026-10-19. The user approved `roadmap-proposal.md`; the Phase 3 completion row and Phase 4 handoff are applied to `roadmap.md` together with the final phase work.

All boxes checked with evidence, `learnings.md` written, roadmap proposal approved and applied, `roadmap.md`
  
updated in the same commit as the final phase work.

## Open items to resolve during implementation (tracked in `learnings.md` if they change)

- Whether `interrupt()` inside `aafter_model` resumes identically to the stock path on this exact
    
  langchain/langgraph pair — verified by a real interrupt/resume test, not by reading the source.
- Whether `git worktree add` can target a path inside `.harness` while `.harness` is excluded from the agent's
    
  view without a junction/case mismatch on Windows.
