---
name: feature-spec
description: Write requirements, plan and validation for a feature before implementing it.
command: /spec
category: coding
---
# Feature spec

A spec is how a change stays reviewable. This skill runs the spec-driven loop the
repository already uses, in the same shape.

## 1. Read the constitution

Read `specs/mission.md`, `specs/tech-stack.md` and `specs/roadmap.md` (or the project's
equivalent). If they do not exist, say so and propose a one-page version instead of
inventing rules. Never edit them silently: propose the change and wait.

## 2. Write three files

Create `specs/<date>-<feature>/` with:

- `requirements.md` — goal, in scope, out of scope, numbered requirements `R1..Rn`, wire
  changes, non-functional constraints, and the exact strings the UI must show. Every
  requirement must be testable: name the observation that proves it.
- `plan.md` — ordered steps, one commit each, engine before renderer, tests inside the
  step that creates the behaviour. Name the files each step touches.
- `validation.md` — a checkbox per requirement, split into automated checks and the
  manual walkthrough, plus the quality gates. No box may be ticked by inspection alone
  when a test can prove it.

## 3. Stop and ask

Present the three files and stop. Implementation starts only when the person approves.
If reality contradicts the spec later, stop and update the spec first, then the code.

## 4. Implement and validate

Follow `plan.md` in order. Write the test named in `validation.md` in the same commit as
the behaviour. Tick a box only with evidence: a test name, a command output, an artifact.
Record deviations and surprises in `learnings.md`, then update the roadmap row.

## Rules

- One phase at a time; do not start the next phase before this one's validation passes.
- No product code before the spec exists and is approved.
- Requirements describe behaviour, not files. Plans describe files.
