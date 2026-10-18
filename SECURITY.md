# Security

CodeHarness is a local, single-user desktop app, not a sandbox or VM.
The engine binds loopback and requires an ephemeral bearer token outside explicit
development mode. The renderer has no Node access. Windows Job Objects own the
engine lifetime. Phase 1 allows workspace file reads only; permissioned writes
and commands arrive in Phase 3.

The path jail resolves symlinks and junctions but cannot prevent a hostile local
process changing a reparse point between resolution and access. Never select an
untrusted workspace expecting OS-level isolation. No telemetry is enabled.
