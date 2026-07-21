#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    echo ".env already exists; leaving it unchanged"
    exit 0
fi

umask 077
plant_token=$(openssl rand -hex 32)
flag_secret=$(openssl rand -hex 32)
instance_suffix=$(openssl rand -hex 4)

{
    printf '%s\n' 'SCADA_PORT=8089'
    printf '%s\n' 'CHECKER_PORT=8090'
    printf '%s\n' 'PLAYER_SSH_PORT=2224'
    printf '%s\n' 'PLAYER_PASSWORD=line4-maint'
    printf 'PLANT_API_TOKEN=%s\n' "$plant_token"
    printf 'FLAG_SECRET=%s\n' "$flag_secret"
    printf 'INSTANCE_ID=last-bottle-%s\n' "$instance_suffix"
    printf '%s\n' 'FLAG_PREFIX=flag'
} > .env

chmod 0600 .env
echo "Created .env with new instance secrets"
