#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

docker compose --profile build build core-image
docker run --rm --user 0 \
    --volume "$PWD/tests:/app/tests:ro" \
    last-bottle-core:${IMAGE_TAG:-local} \
    sh -c 'pip install --quiet pytest==8.4.1 && pytest -q /app/tests'

