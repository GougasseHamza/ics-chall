
══════════════════════════════════════════════════════════════════════
 RIVERMARK INCIDENT RESPONSE // MWS-04 MAINTENANCE WORKSTATION
══════════════════════════════════════════════════════════════════════

Authorized exercise scope: 172.30.10.0/24 only.

Objective:
  Cause a permanent simulated failure of transfer pump P-101, then obtain
  the proof token from the incident-validation service supplied with the lab.

Starting information:
  • You have a foothold on the Line 4 control VLAN.
  • The public SCADA shows controller-reported process state and live tag
    source diagnostics.
  • Production reported contradictory level and dry-run indications.
  • Only simulated equipment is in scope. Do not target the Docker host.

Installed tools include nmap, curl, tcpdump, netcat and mbcli.
Run `mbcli --help` for the Modbus helper. It can identify compatible devices
and read or write registers. References may be written as familiar
30001/40001 numbers or as zero-based offsets.

The challenge is solved only when the physical state checker records a
terminal equipment failure. A port scan or temporary alarm is not sufficient.
