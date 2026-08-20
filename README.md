# Checkmate

Checkmate is an MVP web application for splitting a restaurant receipt based on
the items each person consumed.

The workflow is:

```text
Upload receipt -> Review and edit -> Assign people -> Calculate split -> Generate PDF
```

The application provides editable receipt fields, optional receipt-image
extraction, ordered participants, checkbox assignments, cent-exact tax and tip
allocation, reconciliation, actionable validation, and PDF download. Product
requirements and design documents are under `docs/versions/`;
`docs/versions/CURRENT` identifies the active version.

## Prerequisites

- Git
- `uv` 0.11.32
- Docker Desktop or another Docker engine with Buildx, for the production image

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
| `OPENAI_API_KEY` | absent | Enables automatic receipt extraction through OpenAI |

An invalid host, port, or log level stops startup with a safe configuration
message. `OPENAI_API_KEY` is optional and must be supplied only through the
process environment or a deployment secret store; it is never rendered or
logged.

Manual entry and deterministic splitting work without an OpenAI key. To enable
receipt upload, create a project API key in the
[OpenAI API key dashboard](https://platform.openai.com/api-keys) and supply it
to Checkmate as `OPENAI_API_KEY`. A ChatGPT subscription and API billing are
separate; the API project must have usable credits or billing configured.

### Configure the OpenAI API key

For a session-only setup on macOS or Linux, use a hidden prompt so the key is
not written literally into shell history:

```bash
printf "Paste the full OpenAI API key: "
IFS= read -r -s OPENAI_API_KEY
printf "\n"
export OPENAI_API_KEY
```

The value applies only to the current terminal and to processes started from
it. Verify the credential without printing it:

```bash
curl --silent --show-error \
  --output /dev/null \
  --write-out 'HTTP %{http_code}\n' \
  https://api.openai.com/v1/models \
  --header "Authorization: Bearer $OPENAI_API_KEY"
```

`HTTP 200` confirms authentication. `HTTP 401` means the supplied value is not
an accepted API key; create a new key and copy its full value when it is first
displayed. Never paste a key into an issue, chat, log, or browser form.

On macOS, the login Keychain can retain a verified key between terminal
sessions. First complete the hidden-prompt setup above and confirm `HTTP 200`,
then store that exact environment value:

```bash
security add-generic-password \
  -a "$USER" \
  -s "checkmate-openai-api-key" \
  -U \
  -w "$OPENAI_API_KEY"
```

Load it in each new terminal before starting Checkmate:

```bash
export OPENAI_API_KEY="$(security find-generic-password \
  -a "$USER" \
  -s "checkmate-openai-api-key" \
  -w)"
```

Confirm that Keychain returned a value without displaying the secret:

```bash
test -n "$OPENAI_API_KEY" && echo "OpenAI API key loaded"
```

Then start the local process:

```bash
uv run checkmate-web
```

Never place a real key in source code, Git, browser fields, or a committed
`.env` file. With a key configured, the page accepts one JPEG, PNG, or WebP
receipt image up to 10 MiB. It tells the user before upload that the image is
sent to OpenAI and that every extracted value requires review.

Drafts exist only in the current browser page and disappear on refresh. The
server creates no application-managed receipt files and does not store receipt
or participant data. A missing key or provider failure never stops manual
calculation, the web process, or the health endpoint.

### Public deployment prerequisites

The application container is only one part of a safe public deployment. Before
exposing Checkmate to the internet, the selected ingress and hosting platform
must provide HTTPS and HSTS, enforce the same 10 MiB upload and 256 KiB JSON
body limits, rate-limit receipt extraction, cap per-instance and fleet request
concurrency, and configure only the exact trusted proxy addresses. Configure
OpenAI usage budgets or alerts as an independent cost control. These controls
are deployment requirements; v0.1 does not select or configure a cloud host,
domain, TLS provider, or public ingress.

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

### Production container

Run the following commands from the repository root, where `Dockerfile` is
located. An activated Python or Conda environment does not affect the Docker
build. When copying an example, copy only the command inside its code block,
not the Markdown fence markers. Make sure Docker Desktop or another Docker
engine is running:

```bash
docker version
docker buildx version
```

Build the tested Linux/amd64 production image from the pinned Python and uv
base-image digests. `--load` makes the completed image available to the local
Docker engine:

```bash
docker buildx build \
  --platform linux/amd64 \
  --load \
  --tag checkmate:local \
  .
```

Run the complete image inspection, read-only-filesystem, startup, route, asset,
manual-calculation, PDF, no-key, and shutdown smoke contract:

```bash
uv run python tests/container_smoke_test.py checkmate:local
```

To keep the application running for manual use:

```bash
docker run --rm \
  --name checkmate-local \
  --platform linux/amd64 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --publish 127.0.0.1:8000:8000 \
  --env OPENAI_API_KEY \
  checkmate:local
```

The `--env OPENAI_API_KEY` option passes the variable already loaded in the
current terminal at container startup; it does not bake the secret into the
image. Omit that option to test manual-entry mode without automatic receipt
extraction.

Keep the terminal running and open `http://127.0.0.1:8000/`. From a second
terminal, confirm that the container is healthy:

```bash
curl http://127.0.0.1:8000/health
```

Stop the container with `Control-C`. This release is verified only for
Linux/amd64; on Apple silicon, Docker Desktop runs this image through amd64
emulation. Another architecture needs its own successful build and smoke
evidence.

If Docker reports that `checkmate:local` does not exist, the build did not
finish or was not loaded; rerun the build command and wait for a successful
completion. If port 8000 is already allocated, stop the existing local server
or container before retrying. If the page says extraction is unavailable,
verify that the key is loaded in the same terminal and recreate the container;
a running container cannot inherit later environment changes.

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

The paid provider-quality evaluation is excluded from normal tests. It uses 12
generated fictional receipt layouts and runs only with both an environment key
and the explicit switch:

```bash
uv run pytest --run-external --no-cov \
  tests/external/test_receipt_extraction_evaluation.py -s
```

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
enable the button again. Selecting **Generate PDF** should download the
completed split summary.

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
