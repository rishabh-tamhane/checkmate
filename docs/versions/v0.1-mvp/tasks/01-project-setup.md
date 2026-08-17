# Project Setup

This workstream establishes the reproducible development, verification, and
delivery foundation required before the MVP feature work is considered
complete.

## Project guidance

- [x] Add repository-level agent instructions in `AGENTS.md`.
- [x] Document engineering principles in `docs/ENGINEERING_TENETS.md`.
- [x] Add `docs/versions/CURRENT` as the active-version pointer and document
  the version-switching process.
- [ ] Complete and approve `technical-design.md` before application
  implementation begins.
- [ ] Document local development and verification commands in the root
  `README.md`.

## Runtime and dependencies

- [ ] Select and pin the supported Python version.
- [ ] Create `pyproject.toml` with project metadata and dependency groups.
- [ ] Generate and commit `uv.lock` using `uv`.
- [ ] Confirm `uv sync --locked` succeeds from a fresh checkout.
- [ ] Establish the `src/checkmate/` package layout.

## Engineering tools

- [ ] Configure Ruff formatting and linting.
- [ ] Configure mypy with an appropriately strict baseline.
- [ ] Configure pytest and coverage reporting.
- [ ] Add synthetic test fixtures that contain no real receipt or personal
  data.

## Build and delivery

- [ ] Configure wheel and source-distribution builds.
- [ ] Verify the wheel installs and imports in a clean environment.
- [ ] Create a reproducible production container build.
- [ ] Add continuous integration for lockfile, lint, format, type, test, and
  build checks.
- [ ] Verify the production artifact starts and passes a health check.

## Completion criteria

- [ ] Every command required by `AGENTS.md` is configured and passes.
- [ ] A new contributor can set up, test, build, and run the project by
  following only the committed documentation.
