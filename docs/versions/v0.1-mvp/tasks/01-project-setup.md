# Project Setup

This workstream establishes the reproducible development, verification, and
delivery foundation required before the MVP feature work is considered
complete.

## Project guidance

- [x] Add repository-level agent instructions in `AGENTS.md`.
- [x] Document engineering principles in `docs/ENGINEERING_TENETS.md`.
- [x] Add `docs/versions/CURRENT` as the active-version pointer and document
  the version-switching process.
- [x] Document local development and verification commands in the root
  `README.md`.

## Runtime and dependencies

- [x] Select and pin the supported Python version.
- [x] Create `pyproject.toml` with project metadata and dependency groups.
- [x] Generate `uv.lock` using `uv`.
- [x] Commit `uv.lock` with the project-setup changes.
- [x] Confirm `uv sync --locked` succeeds from a fresh checkout.
- [x] Establish the `src/checkmate/` package layout.
- [ ] Use installed package metadata as the single source of the project
  version, removing the duplicated `0.1.0` literal from
  `src/checkmate/__init__.py`.

## Engineering tools

- [x] Configure Ruff formatting and linting.
- [x] Configure mypy with an appropriately strict baseline.
- [x] Configure pytest and coverage reporting.
- [x] Add synthetic test fixtures that contain no real receipt or personal
  data.

## Build and delivery

The remaining production-container and health-check work is detailed in
[MVP milestone 5](02-mvp-implementation/05-production-readiness.md) and remains
tracked here as a project-setup completion gate.

- [x] Configure wheel and source-distribution builds.
- [x] Verify the wheel installs and imports in a clean environment.
- [ ] Create a reproducible production container build.
- [x] Add continuous integration for lockfile, lint, format, type, test, and
  build checks.
- [ ] Verify the production artifact starts and passes a health check.

## Completion criteria

- [x] Every command required by `AGENTS.md` is configured and passes locally.
- [ ] A new contributor can set up, test, build, and run the project by
  following only the committed documentation.
