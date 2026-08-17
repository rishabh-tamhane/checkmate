# Project Setup Technical Design

## Status

Established. This design records the reproducible development, verification,
and packaging foundation created by the project-setup workstream.

## Runtime and project management

- Python 3.14 is the supported runtime series.
- `.python-version` pins the development and build runtime to Python 3.14.6.
- `pyproject.toml` is the source of project metadata, direct dependencies, and
  tool configuration.
- `uv` 0.11.32 manages Python installation, the virtual environment,
  dependencies, locking, command execution, and builds.
- `uv.lock` records exact direct and transitive dependency resolutions and is
  committed to source control.

## Packaging

- Application code uses the `src/checkmate/` package layout.
- `uv_build` is the PEP 517 build backend.
- Every release must build both a wheel and a source distribution.
- The built wheel must install and import successfully in an isolated
  environment.

## Verification

- Ruff performs formatting and linting.
- mypy performs strict static type checking.
- pytest runs automated tests, with coverage reported by pytest-cov.
- GitHub Actions runs lockfile, lint, format, type, test, build, and isolated
  distribution smoke checks for pull requests and pushes to `main`.
- Core business logic must remain testable without a browser, database,
  external service, network connection, or credentials.
- Synthetic fixtures are stored under `tests/fixtures/`; real receipt or
  personal data is prohibited.

## Application-design boundary

This workstream intentionally does not choose the web framework, UI
architecture, receipt-extraction provider, PDF renderer, application data
models, production process, container layout, hosting platform, or deployment
workflow. Those decisions belong in
[`02-mvp-implementation.md`](02-mvp-implementation.md).
