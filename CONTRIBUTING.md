# Contributing

## Commit Messages

A commit should contain one logical change and its message should explain that
change clearly. Checkmate uses plain imperative commit messages; it does not use
Conventional Commit prefixes such as `feat:`, `fix:`, or `chore:`.

Use this structure:

```text
Imperative summary

Optional explanation of why the change is needed and any important
consequences.

Optional issue reference
```

### Subject

- Start with an imperative verb such as `Add`, `Fix`, `Update`, `Remove`, or
  `Document`.
- Describe what the commit does, as if completing the sentence: "If applied,
  this commit will ..."
- Aim for 50 characters or fewer and never exceed 72 characters.
- Capitalize the first word and do not end with a period.
- Be specific. Avoid messages such as `Update files`, `Changes`, or `WIP`.
- Do not add a type prefix such as `feat:`, `fix:`, or `chore:`.

### Body

Add a body when the motivation or consequences are not obvious from the
subject alone.

- Separate the body from the subject with a blank line.
- Explain why the change is needed and its important effects; do not merely
  list changed files.
- Wrap lines at approximately 72 characters where practical.
- Put issue references at the end, for example `Refs #42` or `Closes #42`.
- Clearly call out a breaking change and how users should adapt to it.

Examples:

```text
Set up Python project foundation
```

```text
Use integer cents for monetary calculations

Binary floating-point arithmetic can introduce fractional-cent errors.
Integer cents keep allocation and remainder distribution deterministic.
```

Before committing, inspect exactly what is staged:

```bash
git status --short
git diff --cached
```

Confirm that the staged changes form one logical unit, contain no secrets or
personal data, and pass the checks required by `AGENTS.md`.

## Ask Codex to Draft a Message

In the Codex CLI or IDE, invoke the repository skill explicitly:

```text
$write-commit-message
```

You can add context to the request:

```text
Use $write-commit-message to draft a message for my staged changes.
```

```text
Use $write-commit-message to review this message: Add receipt validation
```

The skill may inspect Git changes, but it must not stage, commit, or push them
unless you explicitly ask it to do so.
