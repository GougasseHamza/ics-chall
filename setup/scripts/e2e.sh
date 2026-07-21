#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

./scripts/reset.sh >/dev/null
echo "Waiting for reset..."
sleep 8

echo "Verifying the FUXA project and live Modbus bindings..."
scada_port=$(sed -n 's/^SCADA_PORT=//p' .env)
project=$(curl --fail --silent --show-error "http://127.0.0.1:${scada_port}/api/project")
printf '%s' "$project" | grep -q 'Rivermark Line 4 Operations'
printf '%s' "$project" | grep -q '"variableId":"validator_flag"'
printf '%s' "$project" | grep -q '172.30.10.11:502'
printf '%s' "$project" | grep -q '"id":"PIE_conveyor"'
printf '%s' "$project" | grep -q '"id":"GXP_bottle_fill"'
printf '%s' "$project" | grep -q '"type":"clockwise"'
login_status=$(curl --silent --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"123456"}' \
    "http://127.0.0.1:${scada_port}/api/signin")
project_write_status=$(curl --silent --output /dev/null --write-out '%{http_code}' \
    -H 'Content-Type: application/json' -d '{}' \
    "http://127.0.0.1:${scada_port}/api/project")
if [ "$login_status" != "401" ] || [ "$project_write_status" != "401" ]; then
    echo "FUXA editor authentication is not enforcing the expected boundary" >&2
    exit 1
fi

echo "Verifying the player can discover RIO-101 without clue files..."
docker compose exec -T --user player player mbcli identify 172.30.10.13 | grep -q "LT-101 Remote I/O Gateway"
if docker compose exec -T --user player player mbcli read-holding 172.30.10.13 40002 1; then
    echo "Out-of-range RIO register unexpectedly responded" >&2
    exit 1
fi

docker compose exec -T --user player player mbcli write 172.30.10.11 40001 1 >/dev/null
docker compose exec -T --user player player mbcli write 172.30.10.11 40002 1 >/dev/null
sleep 1
baseline=$(docker compose exec -T --user player player mbcli read-input 172.30.10.13 30001 1 | awk '/^30001/{print $5}')
docker compose exec -T --user player player mbcli write 172.30.10.13 40001 500
sleep 1
shifted=$(docker compose exec -T --user player player mbcli read-input 172.30.10.13 30001 1 | awk '/^30001/{print $5}')
delta=$((shifted - baseline))
echo "Controlled calibration test changed the raw level by ${delta} counts"
if [ "$delta" -lt 450 ] || [ "$delta" -gt 550 ]; then
    echo "Controlled RIO calibration change was not observable" >&2
    exit 1
fi
docker compose exec -T --user player player mbcli write 172.30.10.13 40001 0 >/dev/null
docker compose exec -T --user player player mbcli write 172.30.10.11 40001 3 >/dev/null
docker compose exec -T --user player player mbcli write 172.30.10.11 40002 3 >/dev/null

echo "Injecting a false LT-101 calibration value over unauthenticated Modbus..."
docker compose exec -T --user player player mbcli write 172.30.10.13 40001 10000

checker_port=$(sed -n 's/^CHECKER_PORT=//p' .env)
attempt=0
while [ "$attempt" -lt 50 ]; do
    result=$(curl --fail --silent --show-error "http://127.0.0.1:${checker_port}/api/claim")
    echo "$result"
    if printf '%s' "$result" | grep -q '"solved":true'; then
        sleep 2
        docker compose exec -T scada grep -q "Incident Validator.*connect" _logs/fuxa.log
        echo "End-to-end solve and FUXA validation path passed"
        exit 0
    fi
    attempt=$((attempt + 1))
    sleep 2
done

echo "End-to-end solve timed out" >&2
exit 1
