# Security boundaries

The challenge is intentionally vulnerable at the industrial communications
layer. Its PLC safety comparison is deliberately correct, and its hosting
boundary is not intended to be vulnerable.

## Deliberate weaknesses

- trusted-zone Modbus/TCP without protocol authentication;
- writable RIO-101 calibration parameter without client authorization;
- PLC-101 dependence on a single unauthenticated network sensor path;
- player foothold inside the control VLAN.

## Hosting controls

- no host publication of Modbus port 502;
- internal control and field Docker networks;
- separate edge network for three explicit public endpoints;
- no Docker socket or host filesystem mounts;
- non-root core services with read-only filesystems;
- dropped Linux capabilities for core services;
- resource and process limits;
- independent plant API and flag secrets;
- flag present only in checker memory after derivation;
- authoritative physical state unavailable to the player container or HMI.

## Prohibited deployment patterns

- attaching a real PLC, SCADA server or physical actuator;
- using host networking;
- exposing port 502 to the Internet;
- mounting `/var/run/docker.sock` into any challenge container;
- adding the player container to `field_net`;
- reusing the VPS root password as the player password;
- running a shared instance for mutually untrusted teams without accepting
  cross-team resets and solve interference.

Run `scripts/validate-isolation.sh` after every Compose change.
