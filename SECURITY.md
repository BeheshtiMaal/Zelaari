# Security

CodeHarness is a local, single-user desktop app. **It is not a sandbox, and it is not a
virtual machine.** Everything below describes what the app does about that; none of it
changes what a program you approve can do.

## What the layers actually do

**Loopback only, with a per-launch token.** The engine binds `127.0.0.1` on an OS-assigned
port and refuses every route — including `/health` — without the bearer token. The token is
generated fresh in the Electron main process on each launch and never written to disk. The
renderer has no Node access and no API for reading stored keys.

**Process lifetime.** The engine runs under a Windows Job Object with kill-on-close, owned
by a watchdog the app spawns. Closing the window ends the job; anything the engine started
dies with it. This is why a stopped run leaves no orphaned command behind.

**The path jail.** Every file tool resolves the requested path and refuses anything that
lands outside the selected workspace, including through symlinks, junctions, `..`, and
absolute paths. Reads, writes, edits, deletes and snapshots all go through it.

**The permission layer.** Three modes — read-only, ask, auto — plus per-tool rules in
`.harness/rules.json`. In read-only mode a write or command is refused rather than offered.
In ask mode it becomes an approval card showing the risk level, the path or the command, and
a diff where one applies. In auto mode a list of destructive patterns still asks. A schedule
carries its own ceiling, and the stricter of mode and ceiling wins; an unattended run
defaults to read-only and reports instead of acting.

**Keys.** API keys are encrypted with the Windows data-protection API (DPAPI) through
Electron `safeStorage`, stored in `vault.json` in app data, and refused rather than stored in
plaintext if encryption fails. The engine receives them in memory. Model output is redacted
before checkpointing, and message and reasoning events are redacted before they are
persisted. Keys are kept out of child environments, command arguments, logs and URLs.

**Verification and plans.** A run that changed files cannot finish until the workspace's
check command passes; a plan above the size or risk threshold is approved before work starts,
and a step that leaves its declared file scope stops for a person.

## What they do not do

- **No sandbox.** An approved command runs with your privileges. `auto` mode means the
  assistant decides; it does not mean the command is safe.
- **No protection from a hostile local process** running as the same Windows user. The jail
  resolves reparse points but cannot stop another process changing one between resolution
  and access. Loopback auth protects the endpoints from other machines, not from your own
  account.
- **No protection from a hostile workspace.** Opening an untrusted repository is running
  untrusted content: its `.harness/` rules, skills and check command are data the app reads.
  Review them, or use a folder you can restore.
- **No audit beyond the run folder.** Each run writes `events.jsonl` and checkpoints under
  the workspace's `.harness/`. That is evidence of what happened, not a tamper-proof log: a
  local process can edit it.
- **No telemetry.** The app sends nothing anywhere except to the model endpoint you
  configured. The optional live-check script is the one exception, and you invoke it
  yourself.

## What a person should not do

- Do not point it at a folder you cannot restore from version control.
- Do not approve a command you have not read, in any mode.
- Do not put credentials in a workspace: they become context, and context is sent to the
  model.
- Do not run it as an administrator to "make permissions work". The installer is per-user on
  purpose, and elevation only widens what an approved command can do.

## Reporting

This is a personal project with no security team. If you find a hole, open an issue without
the exploit details and say how to reach you.
