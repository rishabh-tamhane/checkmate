# Checkmate

Checkmate is an MVP web application for splitting a restaurant receipt based on
the items each person consumed.

The planned workflow is:

```text
Upload receipt -> Review and edit -> Assign people -> Calculate split -> Generate PDF
```

The application is currently in project setup. Product requirements and design
documents are under `docs/versions/`; `docs/versions/CURRENT` identifies the
active version.

## Prerequisites

- Git
- `uv` 0.11.32
- Docker, once the production container is defined

Install the pinned `uv` version on macOS or Linux using its official standalone
installer:

```bash
curl -LsSf https://astral.sh/uv/0.11.32/install.sh | sh
```

Restart the shell after installation so that `uv` is available on `PATH`.
`uv` installs the pinned Python runtime and project dependencies; a separate
system Python installation is not required.

## Development setup

From the repository root:

```bash
uv python install
uv sync --locked
```

The exact Python patch version is recorded in `.python-version`. Direct project
requirements and tool configuration live in `pyproject.toml`; exact resolved
dependency versions live in the committed `uv.lock`. Do not edit `uv.lock`
manually.

Run commands through `uv` so that they use the project environment:

```bash
uv run python -c "import checkmate; print(checkmate.__version__)"
```

## Verification

Run every required quality gate before completing an application-code or
configuration change:

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
```

The build command creates a wheel and source distribution under `dist/`. Build
artifacts and the local `.venv` are intentionally excluded from Git.

## Documentation

- `AGENTS.md`: concrete repository rules for AI coding agents
- `CONTRIBUTING.md`: contribution and commit-message standards
- `docs/ENGINEERING_TENETS.md`: engineering principles and rationale
- `docs/versions/CURRENT`: active version directory
- `docs/versions/<version>/requirements.md`: product behavior and scope
- `docs/versions/<version>/technical-design.md`: approved implementation design
- `docs/versions/<version>/tasks/`: version workstreams

To ask Codex to draft a commit message from the current Git changes, invoke the
repository skill in the Codex CLI or IDE:

```text
$write-commit-message
```

## License

This project is licensed under the MIT License. See `LICENSE`.
