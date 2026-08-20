#!/bin/sh

set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/../.." && pwd)
cd "$repository_root"

CHECKMATE_IMAGE=unused OPENAI_API_KEY=unused \
    docker compose --project-name checkmate ps

curl --fail --silent --show-error \
    --header "Host: checkmate.rishabhtamhane.com" \
    http://127.0.0.1:8080/health
printf '\n'
