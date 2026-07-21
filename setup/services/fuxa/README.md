# FUXA HMI integration

This directory defines the operator-facing SCADA/HMI for Line 4.

- `Dockerfile` pins the upstream `frangoteam/fuxa:1.3.1` image by digest.
- `project.json` contains the devices, tags, bindings and screen metadata.
- `line4.svg` is the reviewable process mimic rendered by FUXA.
- `seed.js` builds FUXA's ephemeral SQLite project and user databases.
- `entrypoint.sh` seeds the project before starting the normal FUXA server.

FUXA reads PLC-101 and PLC-102 directly over Modbus/TCP. It does not connect to
RIO-101, hold the plant API token, or contain the flag secret. A separate
read-only WebAPI device polls the incident validator, whose proof field remains
null until terminal simulated damage is confirmed.

The mimic animations are driven by PLC tags. P-101 rotates only while PLC-101
reports the pump running, the CV-101 belt moves only while PLC-102 reports the
conveyor running, and the active-bottle gauge fills from PLC-102's bottle-level
input. These are native FUXA actions and gauges rather than independent visual
timers, so a stopped process produces a stopped display.

The editor is authentication-protected. Every container creation generates a
new unrecorded administrator password and JWT secret, leaving players with
guest view access only. The complete FUXA state is held in tmpfs and rebuilt
from these source files on reset.

FUXA is provided by the [FUXA project](https://github.com/frangoteam/FUXA) and
is used here through its published container image under its upstream license.
