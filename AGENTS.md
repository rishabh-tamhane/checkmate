# Agent Instructions

## Project

Checkmate is an MVP web application for splitting a restaurant receipt based on
the items each person consumed.

Before modifying application code:

- Read `docs/versions/CURRENT` to determine the active version directory.
- Read `docs/versions/<active-version>/requirements.md`.
- Read `docs/versions/<active-version>/technical-design.md` to identify the
  applicable technical-design workstream.
- Read the relevant file under
  `docs/versions/<active-version>/technical-design/`.
- Read `docs/ENGINEERING_TENETS.md`.
- Read the relevant task file under
  `docs/versions/<active-version>/tasks/`.

Replace `<active-version>` with the exact single-line value from
`docs/versions/CURRENT`. Do not infer the active version by sorting directory
names. If the pointer is missing, invalid, or references a directory that does
not exist, stop and report the problem before changing application code.

If these documents disagree, stop and describe the conflict before changing
code. Requirements define product behavior; the technical design defines the
approved implementation approach.

Do not modify application code when its applicable technical-design workstream
is missing or has any status other than `Approved`.

## Engineering Rules

1. Do not add a dependency unless it is necessary for an approved requirement
   or technical-design decision.
2. Add and remove Python dependencies with `uv add` and `uv remove`. All
   dependencies must be declared in `pyproject.toml`.
3. Never edit `uv.lock` manually. Generate it with `uv` and commit it whenever
   dependency resolution changes.
4. New or changed business logic must have unit tests. Bug fixes must include a
   regression test when practical.
5. Public Python functions, methods, and classes must have complete type
   annotations.
6. Keep receipt extraction, split calculation, presentation, and external
   service integration separate. In particular, receipt parsing must not
   contain expense-splitting rules.
7. Monetary calculations must be deterministic and must not use binary
   floating-point values. Follow the rounding policy in the technical design.
8. Keep external services behind interfaces so core behavior can be tested
   without network access or credentials.
9. Prefer the simplest implementation that satisfies current requirements. Do
   not add abstractions or infrastructure for hypothetical future versions.
10. Validate data at system boundaries and never silently produce or finalize
    an invalid split.
11. Never commit secrets or real receipt data. Do not log API keys, full receipt
    images, or personal data.
12. Existing tests must continue to pass. Do not weaken or delete a test merely
    to make a change pass without documenting why its expected behavior changed.

## Scope Discipline

- Implement only behavior included in the active version's requirements and
  technical design.
- Record newly discovered future work in the backlog rather than expanding the
  current change without approval.
- Update requirements or technical design before implementing a behavior that
  changes an approved product or architecture decision.

## Commit Messages

- Follow the commit-message standard in `CONTRIBUTING.md`.
- Before suggesting a message, inspect the staged diff. If nothing is staged,
  state that the suggestion is based on unstaged changes.
- Do not use Conventional Commit prefixes such as `feat:`, `fix:`, or `chore:`.
- Do not stage changes, create a commit, or push unless the user explicitly asks
  for that action.

## Before Completing a Change

For application-code or configuration changes, run:

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
```

Run any additional focused tests relevant to the change. Do not claim a change
is complete if a required check fails.

During initial project setup, some commands may not exist yet. In that case,
state which checks could not run and leave the corresponding setup task
incomplete; do not report the missing check as passing.
