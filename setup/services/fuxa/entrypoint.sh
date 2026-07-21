#!/bin/sh
set -eu

cd /usr/src/app/FUXA/server
node /opt/rivermark-fuxa/seed.js
exec "$@"
