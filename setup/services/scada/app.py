"""Lightweight SCADA backend that polls both PLCs over Modbus/TCP."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from pyModbusTCP.client import ModbusClient
from waitress import serve

from services.common.config import (
    MODBUS_PORT,
    PLC1_HOST,
    PLC2_HOST,
    MachineState,
    Mode,
    SCALE_PERCENT,
    SCALE_SECONDS,
    SCALE_TEMPERATURE,
)
app = Flask(__name__)


def client(host: str) -> ModbusClient:
    return ModbusClient(host=host, port=MODBUS_PORT, auto_open=True, auto_close=True, timeout=1.0)


def read_registers(modbus: ModbusClient, kind: str, address: int, count: int) -> list[int]:
    reader = modbus.read_input_registers if kind == "input" else modbus.read_holding_registers
    values = reader(address, count)
    if values is None or len(values) != count:
        raise ConnectionError(f"incomplete {kind} register response")
    return [int(value) for value in values]


def mode_name(value: int) -> str:
    try:
        return Mode(value).name.replace("_", " ")
    except ValueError:
        return f"INVALID ({value})"


def poll_status() -> dict:
    plc1 = client(PLC1_HOST)
    plc2 = client(PLC2_HOST)
    h1 = read_registers(plc1, "holding", 0, 5)
    i1 = read_registers(plc1, "input", 0, 10)
    h2 = read_registers(plc2, "holding", 0, 2)
    i2 = read_registers(plc2, "input", 0, 6)
    try:
        machine_state = MachineState(i1[9]).name
    except ValueError:
        machine_state = "UNKNOWN"

    return {
        "online": True,
        "machine_state": machine_state,
        "tank": {
            "level": i1[0] / SCALE_PERCENT,
            "inlet_open": bool(i1[1]),
            "inlet_mode": mode_name(h1[0]),
            "low_setpoint": h1[2] / SCALE_PERCENT,
            "high_setpoint": h1[3] / SCALE_PERCENT,
            "low_alarm": bool(i1[7]),
        },
        "pump": {
            "running": bool(i1[2]),
            "mode": mode_name(h1[1]),
            "temperature": i1[3] / SCALE_TEMPERATURE,
            "vibration": i1[4] / SCALE_TEMPERATURE,
            "dry_run_seconds": i1[5] / SCALE_SECONDS,
            "damage": i1[6] / SCALE_PERCENT,
            "dry_run_alarm": bool(i1[8]),
        },
        "line": {
            "bottle_level": i2[0] / SCALE_PERCENT,
            "bottle_position": i2[1] / SCALE_PERCENT,
            "conveyor_running": bool(i2[2]),
            "conveyor_mode": mode_name(h2[0]),
            "good_bottles": i2[3],
            "rejected_bottles": i2[4],
            "spill_alarm": bool(i2[5]),
        },
        "events": alarm_events(i1, i2),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def alarm_events(plc1_inputs: list[int], plc2_inputs: list[int]) -> list[dict[str, str]]:
    """Build the operator event list strictly from PLC-reported telemetry."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    events: list[dict[str, str]] = []
    if plc1_inputs[8]:
        events.append({"time": now, "severity": "CRITICAL", "message": "P-101 dry-run alarm active"})
    if plc1_inputs[7]:
        events.append({"time": now, "severity": "WARNING", "message": "TK-101 low-level alarm active"})
    if plc2_inputs[5]:
        events.append({"time": now, "severity": "WARNING", "message": "Filler spill alarm active"})
    if not events:
        events.append({"time": now, "severity": "INFO", "message": "Line 4 process values within reported limits"})
    return events


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/api/status")
def status():
    try:
        return jsonify(poll_status())
    except Exception as exc:
        return jsonify(online=False, error=str(exc)), 503


@app.post("/api/control")
def control():
    body = request.get_json(silent=True) or {}
    action = body.get("action")
    plc1 = client(PLC1_HOST)
    plc2 = client(PLC2_HOST)

    if action == "automatic":
        ok = (
            plc1.write_multiple_registers(0, [int(Mode.AUTO), int(Mode.AUTO)])
            and plc2.write_single_register(0, int(Mode.AUTO))
        )
    elif action == "safe_stop":
        ok = (
            plc1.write_multiple_registers(0, [int(Mode.AUTO), int(Mode.MANUAL_OFF)])
            and plc2.write_single_register(0, int(Mode.MANUAL_OFF))
        )
    else:
        return jsonify(error="unsupported operator action"), 400

    if not ok:
        return jsonify(error="PLC command was not acknowledged"), 503
    return jsonify(ok=True, action=action)


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080, threads=6)
