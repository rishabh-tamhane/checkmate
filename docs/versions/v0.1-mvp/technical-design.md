# v0.1 MVP Technical Design

## Status

Draft. The technical foundation below is established by the project-setup
workstream. Application architecture, external services, and deployment remain
open and must be decided before MVP feature implementation.

## Technical foundation

### Runtime and project management

- Python 3.14 is the supported runtime series.
- `.python-version` pins the development and build runtime to Python 3.14.6.
- `pyproject.toml` is the source of project metadata, direct dependencies, and
  tool configuration.
- `uv` 0.11.32 manages Python installation, the virtual environment,
  dependencies, locking, command execution, and builds.
- `uv.lock` records exact direct and transitive dependency resolutions and is
  committed to source control.

### Packaging

- Application code uses the `src/checkmate/` package layout.
- `uv_build` is the PEP 517 build backend.
- Every release must build both a wheel and a source distribution.
- The built wheel must install and import successfully in an isolated
  environment.

### Verification

- Ruff performs formatting and linting.
- mypy performs strict static type checking.
- pytest runs automated tests, with coverage reported by pytest-cov.
- GitHub Actions runs lockfile, lint, format, type, test, build, and isolated
  distribution smoke checks for pull requests and pushes to `main`.
- Core business logic must remain testable without a browser, database,
  external service, network connection, or credentials.
- Synthetic fixtures are stored under `tests/fixtures/`; real receipt or
  personal data is prohibited.

## Open application decisions

The following decisions are intentionally not made by project setup:

- Server-side web framework and UI architecture
- Receipt extraction provider and fallback behavior
- PDF-generation library and rendering approach
- Request and domain data models
- API and module boundaries
- Production process model, health endpoint, and container layout
- Hosting platform and continuous-delivery workflow

These choices must satisfy `requirements.md` and
`docs/ENGINEERING_TENETS.md` without expanding the v0.1 scope.
