---
name: web-search
description: Search the web for current facts, with every query approved before it leaves the machine.
command: /search
category: web
requires_approval: true
---
# Web search

Use this when the answer depends on something that changes: a release note, a version, a
price, an API shape, an error message from a library published after your training data.
Do not search for things you can read from the workspace.

## Before the query

1. Say what you are looking for and why the workspace cannot answer it.
2. Turn the question into a query a search engine can answer: nouns, version numbers,
   error text in quotes. No full sentences, no secrets, no file contents, no API keys.
3. Every query is an approval card. Read it before you send it: the person can edit the
   query, and the edited text is what runs.

## After the results

- Prefer primary sources: official documentation, release notes, the repository itself.
- Say which URL each claim comes from. A claim without a source is your guess, and you
  must label it as one.
- Quote version numbers and dates exactly; do not round them.
- If the results disagree, say so and prefer the newest primary source.
- If nothing useful comes back, report that and continue with what the workspace has.
  Do not invent a citation.

## Shape of the answer

Short: the finding, the source URL, the version or date it applies to, and what it
changes about the task. Put the links next to the claim they support, not in a pile at
the end.
