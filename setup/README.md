# The Last Bottle

`The Last Bottle` is a standalone industrial-control-system CTF challenge. It
models a beverage bottling cell with one integrated PLC, a Modbus remote-I/O gateway, a
FUXA SCADA/HMI, a physical process, an SSH player workstation, and a
physical-impact flag checker.

The challenge is inspired by the component separation and bottle-filling
scenario in [ICSSIM](https://github.com/AlirezaDehlaghi/ICSSIM), but is an
independent, CTF-focused implementation with hardened container boundaries,
an original process model and FUXA process mimic, a deterministic solve
condition, and operations tooling.

## Challenge summary

The player starts on a maintenance workstation inside the Line 4 control VLAN.
PLC-101 controls tank TK-101 and transfer pump P-101 using a level value from
RIO-101. Legacy Modbus/TCP provides no authentication or message-integrity
protection, so an unauthorized calibration write can falsify that value. The
PLC retains its low-level permissive but makes an unsafe decision from trusted,
false telemetry. The flag is issued only after the independent physics model
records sustained dry running and terminal mechanical damage.

Discovery comes from the live system rather than hidden answer files. FUXA
polls PLC-101 over Modbus/TCP and displays its live process tags.
Its pump, product-flow, conveyor and bottle-fill animations are driven by those PLC tags, so
the mimic starts and stops with the simulated equipment.
Modbus device identification describes each endpoint, and deliberately bounded
register maps let players test a small number of meaningful addresses while
receiving normal Modbus exceptions for invalid probes. The HMI never connects
to vulnerable RIO-101, so it does not reveal the intended write target.

The scenario is inspired by the real FrostyGoop incident behavior documented
by Dragos and MITRE ATT&CK: reading and writing Modbus holding registers to
modify parameters and disrupt an industrial process. It is an original safe
simulation, not a copy of the malware or the affected heating installation.

## Public endpoints

| Service | Default endpoint | Purpose |
|---|---|---|
| FUXA SCADA/HMI | `http://HOST:8089` | Live process mimic, telemetry, alarms and flag banner |
| Checker | `http://HOST:8090` | Physical-impact validation and flag claim |
| Player SSH | `ssh player@HOST -p 2224` | Isolated workstation on the OT control VLAN |

Default player password: `line4-maint`. This is an intended challenge
credential, not a host credential.

Modbus/TCP port 502 is never published on the host.

## VPS deployment

```sh
cd /opt/last-bottle
chmod +x scripts/*.sh
./scripts/test.sh
./scripts/deploy.sh
./scripts/validate-isolation.sh
```

The deploy script generates a mode-0600 `.env` containing independent plant
and flag secrets. Existing `.env` files are never overwritten.

Useful commands:

```sh
./scripts/status.sh
./scripts/reset.sh
./scripts/e2e.sh
docker compose logs -f --tail=100
```

## Documentation

- [Documentation index](docs/README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Operations runbook](docs/OPERATIONS.md)
- [Challenge author guide and intended solution](docs/AUTHOR_GUIDE.md)
- [Player brief](docs/PLAYER_BRIEF.md)
- [Security boundaries](docs/SECURITY.md)
- [Official walkthrough](../writeup/README.md) (**spoilers and flag evidence**)

## Repository structure

```text
setup/
├── compose.yaml                 # Isolated control, field and edge networks
├── services/
│   ├── attacker/                # Player SSH workstation and mbcli helper
│   ├── checker/                 # Independent physical-impact validator
│   ├── common/                  # Shared runtime image and helpers
│   ├── plant/                   # Authoritative physical-process model
│   ├── plc1/                    # Integrated bottling-cell controller
│   ├── rio/                     # Vulnerable LT-101 remote-I/O gateway
│   └── fuxa/                    # Pinned FUXA image, project, SVG and secure seeder
├── scripts/                     # Deploy, reset, test and isolation checks
├── tests/                       # Unit tests for configuration and physics
└── docs/
    ├── README.md                # Documentation map and release rules
    ├── PLAYER_BRIEF.md          # Material safe to give competitors
    ├── ARCHITECTURE.md          # Components, networks and trust boundaries
    ├── OPERATIONS.md            # VPS deployment and event runbook
    ├── SECURITY.md              # Intended vulnerability and containment
    ├── AUTHOR_GUIDE.md          # Register map and intended solution
    └── assets/                  # Rendered architecture diagrams and sources
```

`docs/PLAYER_BRIEF.md` is the only document intended for players before the
event. The author guide and external walkthrough disclose the solve path.

## Safety

This repository is intentionally vulnerable for an authorized CTF. Run it only
on an isolated server. Never attach its control network to real PLCs, SCADA
systems, industrial equipment, or third-party networks.
