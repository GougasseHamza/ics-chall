"""Issue a deterministic instance flag only after physical pump failure."""

from __future__ import annotations

import hashlib
import hmac
import os

from flask import Flask, jsonify, render_template
from waitress import serve

from services.common.config import MachineState
from services.common.http import get_plant_state


app = Flask(__name__)


def instance_flag() -> str:
    secret = os.environ["FLAG_SECRET"].encode()
    instance = os.getenv("INSTANCE_ID", "last-bottle-01")
    prefix = os.getenv("FLAG_PREFIX", "flag")
    digest = hmac.new(secret, f"{instance}:pump-broken".encode(), hashlib.sha256).hexdigest()[:24]
    return f"{prefix}{{last_bottle_{digest}}}"


def challenge_state() -> dict:
    state = get_plant_state()
    solved = bool(
        state["machine_state"] == int(MachineState.BROKEN)
        and state["pump_damage"] >= 100.0
        and state["dry_run_seconds"] >= 9.0
    )
    return {
        "solved": solved,
        "machine_state": MachineState(state["machine_state"]).name,
        "pump_damage": round(state["pump_damage"], 1),
        "pump_temperature": round(state["pump_temperature"], 1),
        "dry_run_seconds": round(state["dry_run_seconds"], 1),
        "flag": instance_flag() if solved else None,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/api/claim")
def claim():
    return jsonify(challenge_state())


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080, threads=4)
