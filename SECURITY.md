# Security

CodeHarness is a local, single-user desktop app, not a sandbox or VM.
The engine binds loopback and requires an ephemeral bearer token outside explicit
development mode. The renderer has no Node access. Windows Job Objects own the
engine lifetime. Phase 1 allows workspace file reads only; permissioned writes
and commands arrive in Phase 3.

The path jail resolves symlinks and junctions but cannot prevent a hostile local
process changing a reparse point between resolution and access. Never select an
untrusted workspace expecting OS-level isolation. No telemetry is enabled.

Phase 2 stores API keys as safeStorage ciphertext in Electron app data, outside
workspaces, and refuses plaintext fallback. Stored keys have no renderer read API.
The engine receives keys in memory and redacts returned model content before
checkpointing, plus message/reasoning events before persistence. Plaintext keys are
omitted from child environments, command arguments, logs and URLs. Loopback auth
protects local endpoints, not a hostile process running as the same Windows user.
