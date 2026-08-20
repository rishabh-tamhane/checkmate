#!/bin/sh

set -eu

if [ "$#" -ne 1 ]; then
    printf '%s\n' "Usage: $0 checkmate:hosting-<commit>" >&2
    exit 1
fi

CHECKMATE_IMAGE=$1
case "$CHECKMATE_IMAGE" in
    checkmate:hosting-[0-9a-f]*) ;;
    *)
        printf '%s\n' "Rollback requires a recorded Checkmate hosting tag." >&2
        exit 1
        ;;
esac

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/../.." && pwd)
cd "$repository_root"

if ! docker image inspect "$CHECKMATE_IMAGE" >/dev/null 2>&1; then
    printf '%s\n' "The requested rollback image is not available locally." >&2
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

export CHECKMATE_IMAGE OPENAI_API_KEY
trap 'unset OPENAI_API_KEY' EXIT

docker compose --project-name checkmate up --detach --no-build app
docker compose --project-name checkmate restart ingress
docker compose --project-name checkmate up --detach --no-build --wait

printf '%s\n' "Rollback is healthy: $CHECKMATE_IMAGE"
