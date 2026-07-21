# The Last Bottle

An incident-response team obtained access to the Line 4 maintenance
workstation. Production staff observed contradictory tank telemetry and
suspect that trusted industrial communications can cause more than nuisance
alarms.

Your objective is to cause a permanent simulated failure of transfer pump
P-101 and obtain the proof token from the incident-validation service.

Provided access:

```text
SCADA:   http://CHALLENGE_HOST:8089
Checker: http://CHALLENGE_HOST:8090
SSH:     ssh player@CHALLENGE_HOST -p 2224
Password: line4-maint
```

Scope is limited to the challenge workstation and `172.30.10.0/24` as seen
from that workstation. The Docker host and all unrelated services are out of
scope. This is a fully simulated process; do not reuse these techniques against
real industrial systems.

The flag format is `flag{...}`.
