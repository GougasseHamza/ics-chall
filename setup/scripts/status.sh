#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
docker compose ps
echo
curl --fail --silent --show-error "http://127.0.0.1:$(sed -n 's/^SCADA_PORT=//p' .env)/api/status"
echo
curl --fail --silent --show-error "http://127.0.0.1:$(sed -n 's/^CHECKER_PORT=//p' .env)/api/claim"
echo

