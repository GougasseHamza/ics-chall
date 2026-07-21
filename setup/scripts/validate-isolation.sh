#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

published=$(docker compose ps --format json | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
try:
    parsed = json.loads(raw)
    data = parsed if isinstance(parsed, list) else [parsed]
except json.JSONDecodeError:
    data = [json.loads(line) for line in raw.splitlines() if line.strip()]
for item in data:
    for publisher in item.get("Publishers") or []:
        if publisher.get("PublishedPort"):
            print("{}:{}->{}".format(item.get("Service"), publisher.get("PublishedPort"), publisher.get("TargetPort")))
')

echo "$published"
if echo "$published" | grep -q -- '->502'; then
    echo "ERROR: Modbus port 502 is published" >&2
    exit 1
fi

for network in last-bottle_control_net last-bottle_field_net; do
    internal=$(docker network inspect "$network" --format '{{.Internal}}')
    if [ "$internal" != "true" ]; then
        echo "ERROR: $network is not internal" >&2
        exit 1
    fi
done

echo "Isolation validation passed"
