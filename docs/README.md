# Project Documentation

Long-lived engineering principles live at the top level of `docs/`. Product
requirements, technical design, tests, and implementation tasks are grouped by
version under `docs/versions/`.

## Active version

`docs/versions/CURRENT` contains the directory name of the version currently
being implemented. It is the single source of truth used by repository-level
agent instructions and development workflows.

The file must contain exactly one version-directory name, for example:

```text
v0.1-mvp
```

When work moves to another version:

1. Create the new directory under `docs/versions/`.
2. Add and approve its requirements, technical design, tests, and task list.
3. Change `docs/versions/CURRENT` to the new directory name in the same reviewed
   change that activates the version.

Do not select the active version by sorting directory names. Multiple versions
may exist simultaneously, and the highest-looking version may not be the one
currently being implemented.
