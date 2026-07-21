# The Last Bottle

An intentionally vulnerable industrial-control-system CTF based on a fictional
beverage bottling line. Players use Modbus/TCP from an isolated maintenance
workstation to manipulate a remote-I/O calibration register and cause a
verified simulated pump failure. A pinned FUXA SCADA instance displays the
live process and releases the proof flag in its incident banner after the
independent checker validates the damage.

## Repository structure

```text
the-last-bottle/
├── README.md
├── setup/                    # Deployable challenge, services and operations docs
└── writeup/                  # Official solution, diagrams and screenshots
```

## Setup

The complete deployable project is under [`setup`](setup/README.md). On the
challenge VPS:

```sh
sudo mkdir -p /opt/last-bottle
sudo cp -a setup/. /opt/last-bottle/
cd /opt/last-bottle
chmod +x scripts/*.sh
./scripts/test.sh
./scripts/deploy.sh
./scripts/validate-isolation.sh
```

Default public services:

| Service | Endpoint |
|---|---|
| Player SSH | `ssh player@CHALLENGE_HOST -p 2224` |
| SCADA/HMI | `http://CHALLENGE_HOST:8089` |
| Checker | `http://CHALLENGE_HOST:8090` |

The intended player credential is documented in the setup guide. Modbus port
502 remains private to the isolated Docker control network.

## Write-up

The [official write-up](writeup/README.md) contains the full solve, vulnerable
register, damaging command, architecture diagrams, all 16 captured screenshots
and instance flag evidence. Do not distribute `writeup/` during a live event.

This challenge is a simulation for authorized training. Never connect its
control network to real industrial equipment or expose its Modbus services to
the Internet.
