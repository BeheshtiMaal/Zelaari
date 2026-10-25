---
name: read-framework-docs
description: Read a framework's local documentation and return a short, cited summary.
category: docs
enabled: false
---
# Read framework docs

An example project skill: it lives in this project's `.harness/skills/`, is off by
default, and shows what a project-specific capability looks like. Switch it on in
Customize › Skills when the task needs it.

## Where to look

1. `docs/` and `references/` inside the workspace, then `node_modules/<package>/README.md`
   or the installed package's `docs/` folder.
2. The version in the lockfile decides which page is correct. Read it before quoting.
3. Prefer the file the repository actually ships over anything you remember.

## What to return

- The rule or API in one or two sentences.
- The exact file path and heading it came from.
- The version it applies to.
- One short example, taken from the docs or written to match their shape.

## Rules

- Never invent an option, a prop or a default. If the docs do not say, say that.
- Never paste a whole page. Quote the sentence that answers the question.
- If the local docs are missing or stale, say so and offer to search the web instead
  (which needs its own approval).
