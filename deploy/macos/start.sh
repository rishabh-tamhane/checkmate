#!/bin/sh

set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/../.." && pwd)
cd "$repository_root"

if [ "$(uname -s)" != "Darwin" ]; then
    printf '%s\n' "This helper supports the approved macOS host only." >&2
    exit 1
fi

for command_name in docker git security; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf '%s\n' "Required command is unavailable: $command_name" >&2
        exit 1
    fi
done

if ! docker info >/dev/null 2>&1; then
    printf '%s\n' "Docker is not running. Start Docker Desktop and retry." >&2
    exit 1
fi

if ! git diff --quiet -- . || ! git diff --cached --quiet -- .; then
    printf '%s\n' \
        "Commit or restore tracked changes before creating a release image." >&2
    exit 1
fi
untracked_runtime_files=$(git ls-files --others --exclude-standard -- \
    .dockerignore .github .gitignore Dockerfile README.md compose.yaml deploy \
    docs pyproject.toml src tests uv.lock)
if [ -n "$untracked_runtime_files" ]; then
    printf '%s\n' \
        "Commit or remove untracked runtime files before creating a release image." >&2
    exit 1
fi

keychain_account=$(id -un)
if ! OPENAI_API_KEY=$(security find-generic-password \
    -a "$keychain_account" \
    -s "checkmate-openai-api-key" \
    -w 2>/dev/null); then
    printf '%s\n' \
        "The checkmate-openai-api-key item is unavailable in macOS Keychain." >&2
    exit 1
fi
if [ -z "$OPENAI_API_KEY" ]; then
    printf '%s\n' "The macOS Keychain item is empty." >&2
    exit 1
fi

CHECKMATE_IMAGE="checkmate:hosting-$(git rev-parse --short=12 HEAD)"
export CHECKMATE_IMAGE OPENAI_API_KEY
trap 'unset OPENAI_API_KEY' EXIT

docker compose --project-name checkmate up --detach --build --wait

printf '%s\n' "Checkmate is healthy on the loopback ingress."
printf '%s\n' "Image: $CHECKMATE_IMAGE"
printf '%s\n' \
    "Local health: curl -H 'Host: checkmate.rishabhtamhane.com' http://127.0.0.1:8080/health"
