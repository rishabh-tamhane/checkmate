#!/bin/sh

set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_directory/../.." && pwd)
cd "$repository_root"

CHECKMATE_IMAGE=unused OPENAI_API_KEY=unused \
    docker compose --project-name checkmate stop
