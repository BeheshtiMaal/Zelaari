---
name: grill-me
description: Interview the user until the task is fully specified, one question batch at a time.
command: /grill
category: coding
---
# Grill me

Use this when a request is understandable but not yet buildable: the goal is clear, the
edges are not. Your job is to remove ambiguity before any file changes.

## How to run the interview

1. Read what already exists before asking anything: the workspace, the relevant files,
   the task text. Never ask a question the repository already answers.
2. Ask **one batch** of structured questions with `ask_user_question`. A batch is two to
   four questions that belong together. Do not ask a second batch in the same turn.
3. Use the answer to decide the next batch. If an answer opens a new branch that matters,
   ask about it; if it closes one, drop the questions you had prepared for it.
4. Never repeat a question that has been answered, and never re-ask it in different words
   to "confirm". Treat the answer as settled.

## What must be settled

- **Objective**: the outcome the person will judge, in one sentence.
- **Scope**: what is in, and explicitly what is out.
- **Constraints**: stack, compatibility, data that must not change, deadlines that change
  the design.
- **Acceptance**: how the person will know it works (a command, a screen, a behaviour).
- **Risk**: the one thing most likely to make this fail.

## When to stop

Call `finish_interview` with a short structured summary once objective, scope,
constraints and acceptance are specified and nothing is ambiguous. Then start the work.

Do not implement, write files, or run mutating commands while the interview is open: the
harness blocks them, and asking for permission you know will be refused wastes the
person's attention. A declined interview ends the task: report what is still open and
stop.

## Tone

Ask like a senior engineer who has to build it: concrete, short, no questionnaire. Offer
options when a choice is real, and say which one you would pick and why.
