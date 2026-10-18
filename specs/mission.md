# Mission

## What
**CodeHarness** (working title) is a standalone, installable Windows desktop app that connects any LLM to a real
development environment. Given a coding task it analyzes the problem, plans, edits files, runs and tests code, fixes its own
failures, and keeps going until the task is solved. The human decides on anything sensitive.

## Why (from the challenge brief)
The harness is the bridge between the model's "brain" and a real execution environment. Other people's models must be able to
use it "easily and without hassle": install the app, paste an API key, pick a folder, give a task.

## Who
- Developers who use alternative or cheaper models (DeepSeek, GLM, any OpenAI-compatible endpoint, Anthropic) and want a harness that works.
- Challenge evaluators who install the .exe and judge the five axes below.

## The five axes (product terms)
1. **Files + terminal**: read, edit, create files; run commands (tests, installs, scripts); read their output.
2. **Planning**: analyze first, split into small steps, follow the plan step by step, show live progress.
3. **Skills**: add abilities as folders (docs reading for a framework, web search, custom tools) that the agent loads when relevant.
4. **Code quality + self-correction**: clean, modular, testable output; on errors the agent enters a bounded fix loop until it passes.
5. **Human in the loop**: approvals for risky commands, edits to protected files, and leaving the plan; the human can approve, edit, or reject.

## Differentiators
- **GenUI via OpenUI**: questions, plan, approvals with diffs, test results and terminal output are rendered as real interactive UI.
- **AskUserQuestion**: the agent can stop and ask structured questions (choice, multi-select, ranking, free text), including a **grill-me** mode that interviews the user until the task is fully specified.
- **Spec-driven by default**: a bundled `feature-spec` skill lets the harness itself run constitution -> feature spec -> implement -> validate.
- **Design lineage**: same product shape as onboard-harness (local-first app, workspace folder, approvals inbox, permissions per tool and folder, resumable runs, event log, skills/agents/rules/memory), retargeted from office work to coding.

## License
MIT. Design inspired by onboard-harness (AGPL-3.0); no code is copied from it.

## Non-goals (v1)
- No cloud, accounts, or telemetry. No real sandbox/VM isolation (we state this honestly in SECURITY.md).
- No IDE replacement. No macOS/Linux installers (code must not block them later). No auto-update, no code signing.

## Success criteria
- Fresh Windows machine: install, add a model + key, pick a folder, solve a failing-test task in under 5 minutes.
- Every risky action produces an approval card; rejecting it never crashes the run.
- The same task works on at least one OpenAI-compatible model and one Anthropic model; a built-in **demo model** works with no key and no internet.
- Deliverables exist: Windows installer (.exe) and portable zip.
