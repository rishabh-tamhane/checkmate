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
5. Identify tracked work represented by the changes. When the diff includes a
   task document, inspect its checkbox transitions and summarize only tasks
   changed from incomplete to complete by this commit. Do not claim tasks that
   were already checked. Record the exact task-document path.
6. Draft a specific imperative subject. Do not use a type prefix or ending
   period. Aim for 50 characters or fewer and never exceed 72 characters.
7. Add a body when the motivation or consequences are not obvious. For a large
   task-driven commit, explain the purpose and summarize the main implemented
   outcomes with concise bullets; do not copy every checkbox or list changed
   files. Leave a blank line after the subject and wrap lines at approximately
   72 characters.
8. Put references last. Use `Refs` or `Closes` for issue numbers. When a
   repository task document is relevant, add `Task reference:` followed by its
   exact path. Do not imply that every task in that document is complete.
9. Avoid sensitive data and claims that the inspected changes do not support.
10. Return one recommended message in a `text` code fence. Offer alternatives
   only when they represent meaningful wording or scope choices.
11. Do not stage, commit, or push unless the user explicitly requests it.
