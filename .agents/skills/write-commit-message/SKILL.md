---
name: write-commit-message
description: Draft or review a Checkmate Git commit message from staged or working-tree changes. Use when the user asks for a commit message, wants a message reviewed, or is preparing a commit. Follow CONTRIBUTING.md and do not stage, commit, or push unless explicitly requested.
---

# Write Commit Message

1. Read `CONTRIBUTING.md`, especially the `Commit Messages` section.
2. Inspect `git status --short`.
3. Prefer staged changes. Inspect `git diff --cached --stat` and
   `git diff --cached`. If nothing is staged, inspect `git diff --stat` and
   `git diff`, then state that the recommendation covers unstaged changes.
4. Check whether the changes form one logical unit. If they do not, recommend
   splitting them and provide one message per unit.
5. Draft a specific imperative subject. Do not use a type prefix or ending
   period. Aim for 50 characters or fewer and never exceed 72 characters.
6. Add a body only when the motivation or consequences are not obvious. Leave
   a blank line after the subject, explain why and impact, and wrap lines at
   approximately 72 characters. Put issue references last.
7. Avoid sensitive data and claims that the inspected changes do not support.
8. Return one recommended message in a `text` code fence. Offer alternatives
   only when they represent meaningful wording or scope choices.
9. Do not stage, commit, or push unless the user explicitly requests it.
