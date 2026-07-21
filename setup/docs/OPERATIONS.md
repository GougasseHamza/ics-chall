# Operations runbook

## Requirements

- Linux VPS with Docker Engine and Docker Compose v2
- 2 CPU cores
- 2 GB RAM minimum; 4 GB recommended
- Approximately 2 GB free disk during the first image build
- Host ports 2224, 8089 and 8090 available

The current production path is `/opt/last-bottle`.

## First deployment

```sh
cd /opt/last-bottle
chmod +x scripts/*.sh
./scripts/test.sh
./scripts/deploy.sh
./scripts/validate-isolation.sh
```

Do not manually publish PLC port 502. Do not attach `control_net` or
`field_net` to a host, macvlan, VPN, or real OT segment.

## Routine checks

```sh
./scripts/status.sh
docker compose ps
docker compose logs --tail=100 plant rio plc1 plc2 scada checker
docker stats --no-stream
```

Expected healthy services:

```text
plant rio plc1 plc2 scada checker player
```

The `core-image` service is build-only and does not run.

## Reset after a solve

```sh
./scripts/reset.sh
```

This recreates the physical process, RIO-101, both PLCs, checker and SCADA. The
player container remains available. The transmitter bias returns to zero, PLC
registers return to automatic mode and physical state returns to its safe
initial values.

## End-to-end author test

```sh
./scripts/e2e.sh
./scripts/reset.sh
```

The test verifies device identification, bounded invalid-address behavior and
a small observable calibration change from the unprivileged player container.
It then writes the false LT-101 bias and waits for the checker to emit a flag.
It normally takes 70 to 90 seconds including recreation and health checks.

## Updating code

```sh
cd /opt/last-bottle
./scripts/test.sh
docker compose --profile build build core-image player
docker compose up -d --no-build --force-recreate
./scripts/validate-isolation.sh
```

The deploy script preserves an existing `.env`. Delete or rotate `.env` only
when intentionally changing the instance flag and internal API token.

## Ports and firewall

Only these challenge ports should be reachable:

- TCP/2224: player SSH
- TCP/8089: SCADA
- TCP/8090: incident validator

For a private event, allow these ports only from the event VPN or participant
IP ranges. Port 502 must remain absent from host firewall rules and Docker
publish mappings.

## Backups

The challenge has no persistent gameplay data. Back up only:

- repository source;
- `.env` if the current flag must remain stable;
- reverse-proxy or firewall configuration managed outside this repository.

Do not back up container writable layers.

## Multiple teams

The default Compose project is a single shared instance. For concurrent teams,
deploy one project per team with unique:

- Compose project name;
- host ports;
- Docker subnets;
- `INSTANCE_ID` and `FLAG_SECRET`.

Do not put multiple teams in the same player container: one team could reset or
solve the shared physical process for everyone.
