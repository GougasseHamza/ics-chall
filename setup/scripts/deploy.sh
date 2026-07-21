#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

./scripts/generate-env.sh

echo "Building challenge images..."
docker compose --profile build build core-image player

echo "Starting isolated challenge stack..."
docker compose up -d --no-build --remove-orphans

echo "Waiting for services to report healthy..."
attempt=0
while [ "$attempt" -lt 30 ]; do
    unhealthy=$(docker compose ps --format json | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
try:
    parsed = json.loads(raw)
    data = parsed if isinstance(parsed, list) else [parsed]
except json.JSONDecodeError:
    data = [json.loads(line) for line in raw.splitlines() if line.strip()]
required = {"plant", "rio", "plc1", "plc2", "scada", "checker", "player"}
ready = {item.get("Service") for item in data if item.get("State") == "running" and item.get("Health") in ("", "healthy")}
print("0" if required <= ready else "1")
')
    if [ "$unhealthy" = "0" ]; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ "$attempt" -ge 30 ]; then
    echo "Deployment did not become healthy in time" >&2
    docker compose ps >&2
    exit 1
fi

host_ip=$(hostname -I | awk '{print $1}')
echo "Deployment healthy"
echo "SCADA:   http://${host_ip}:$(sed -n 's/^SCADA_PORT=//p' .env)"
echo "Checker: http://${host_ip}:$(sed -n 's/^CHECKER_PORT=//p' .env)"
echo "Player:  ssh player@${host_ip} -p $(sed -n 's/^PLAYER_SSH_PORT=//p' .env)"
