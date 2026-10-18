# Phase 0 spike evidence (in progress)

No experiment is marked supported until its checks run. This document records findings as they become available.

## Environment
- Windows host, repository `E:\Agentic\Harness`.
- uv selected managed CPython 3.12.14 (system default is 3.10.5; do not use it).
- Node 24.18.0, npm 11.16.0, uv 0.12.19, Git 2.46.0.windows.1.
- Initialized local Git because the supplied folder was not a repository. No remote configured.
- Exact dependency resolution: `spikes/python/uv.lock`, `spikes/ui/package-lock.json` (once installed).

## Verification sources
- Installed package source and declarations are authoritative for these pinned experiments.
- [deepagents distribution](https://pypi.org/project/deepagents/).
- [OpenUI React API](https://www.openui.com/docs/api-reference/react-lang): component definitions, library prompt, renderer and structured errors.
- [Next static export](https://nextjs.org/docs/app/guides/static-exports).
- [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects): process membership and kill-on-close lifetime.

## Outcomes
- Dependency/toolchain setup: in progress.
- OpenUI protocols and rendering: unverified.
- Packaged sidecar lifetime: unverified.
- deepagents APIs and scripted demo: unverified.
- Provider reasoning transport: unverified; synthetic adapter evidence will not establish live endpoint behavior.
- Windows containment: unverified; link privilege and race limitations must be recorded.

## Proposed constitution changes
None established yet. Amendments require explicit approval before application.

## Outstanding work
Complete plan steps 1–7 and attach test evidence before marking Phase 0 complete.
