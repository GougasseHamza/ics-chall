#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "Missing .env; run scripts/deploy.sh first" >&2
    exit 1
fi

echo "Recreating process, remote I/O and controllers in a known-safe state..."
docker compose up -d --no-build --force-recreate plant rio plc1 checker scada
docker compose ps
