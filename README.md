# Checkmate

Checkmate is an MVP web application for splitting a restaurant receipt based on
the items each person consumed.

The planned workflow is:

```text
Upload receipt -> Review and edit -> Assign people -> Calculate split -> Generate PDF
```

The application now provides the complete manual splitting workflow: editable
receipt fields, ordered participants, checkbox assignments, cent-exact tax and
tip allocation, reconciliation, and actionable validation. Automatic receipt
extraction and PDF generation are subsequent milestones. Product requirements
and design documents are under `docs/versions/`; `docs/versions/CURRENT`
identifies the active version.

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
uv run playwright install chromium
```

The exact Python patch version is recorded in `.python-version`. Direct project
requirements and tool configuration live in `pyproject.toml`; exact resolved
dependency versions live in the committed `uv.lock`. Do not edit `uv.lock`
manually. Chromium is installed separately because Playwright browser binaries
are development tools rather than Python packages in `uv.lock`.

Run commands through `uv` so that they use the project environment:

```bash
uv run python -c "import checkmate; print(checkmate.__version__)"
```

## Run the web application

Start the same installed entry point used by the production runtime:

```bash
uv run checkmate-web
```

Open `http://127.0.0.1:8000/` or `http://localhost:8000/` for the manual
splitting application; do not use `http://0.0.0.0:8000/`. Process health is
available at `http://127.0.0.1:8000/health`.

The entry point runs one Uvicorn process without automatic reload. After
changing Python code, stop it with `Control-C` and start it again. If frontend
changes do not appear, hard-refresh the browser with `Command-Shift-R`.

The process reads these environment variables at startup:

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | Listen on every available network interface |
| `PORT` | `8000` | Listening TCP port |
| `LOG_LEVEL` | `info` | `critical`, `error`, `warning`, `info`, `debug`, or `trace` |
| `OPENAI_API_KEY` | absent | Reserved for milestone 3 receipt extraction |

An invalid host, port, or log level stops startup with a safe configuration
message. `OPENAI_API_KEY` is optional and must be supplied only through the
process environment or a deployment secret store; it is never rendered or
logged.

Manual entry and deterministic splitting work without an OpenAI key. Drafts
exist only in the current browser page and disappear on refresh; the server
stores no receipt or participant data. Automatic extraction arrives in
milestone 3. A missing OpenAI key never stops manual calculation, the web
process, or the health endpoint.

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

### Browser tests

The normal `uv run pytest` command runs the Playwright tests with Chromium in
headless mode, so no browser window appears. To watch the complete browser suite
run in a visible Playwright-controlled Chromium window:

```bash
uv run pytest tests/test_browser_workflow.py \
  --headed \
  --browser chromium \
  --slowmo=500 \
  -s
```

To watch only the primary manual-splitting scenario:

```bash
uv run pytest \
  tests/test_browser_workflow.py::test_manual_entry_calculates_exact_totals_and_enables_export_state \
  --headed \
  --browser chromium \
  --slowmo=750 \
  -s
```

`--headed` displays the browser, and `--slowmo` adds a delay in milliseconds
between browser actions. The test window closes automatically when the test
finishes.

## Test the application manually

Start Checkmate from the repository root:

```bash
uv run checkmate-web
```

Keep that terminal running and open `http://127.0.0.1:8000/` in your browser.
Try this synthetic receipt:

1. Add participants `Maya` and `Alex`.
2. Enter an item named `Synthetic noodles` with quantity `2` and line total
   `10.01`.
3. Assign the item to both participants.
4. Enter subtotal `10.01`, tax `1.00`, tip `2.00`, and total `13.01`.

The calculation status should become **Ready**. Maya should owe `$6.51`, Alex
should owe `$6.50`, and the participant totals should add up to `$13.01`.
Changing the subtotal to `9.00` should display a reconciliation error and
disable **Generate PDF**. Correcting it to `10.01` should clear the error and
enable the button again. PDF generation itself is implemented in milestone 4.

Stop the local server by returning to its terminal and pressing `Control-C`.

## Documentation

- `AGENTS.md`: concrete repository rules for AI coding agents
- `CONTRIBUTING.md`: contribution and commit-message standards
- `docs/ENGINEERING_TENETS.md`: engineering principles and rationale
- `docs/versions/CURRENT`: active version directory
- `docs/versions/<version>/requirements.md`: product behavior and scope
- `docs/versions/<version>/technical-design.md`: technical-design workstream
  index
- `docs/versions/<version>/technical-design/`: workstream-specific designs
- `docs/versions/<version>/tasks/`: version workstreams

To ask Codex to draft a commit message from the current Git changes, invoke the
repository skill in the Codex CLI or IDE:

```text
$write-commit-message
```

## License

This project is licensed under the MIT License. See `LICENSE`.
