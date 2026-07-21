"""HTTP wrapper and timing loop for the physical process model."""

from __future__ import annotations

import os
import threading
import time

from flask import Flask, abort, jsonify, request
from waitress import serve

from services.plant.model import PlantModel


app = Flask(__name__)
model = PlantModel()


def require_token() -> None:
    expected = os.environ["PLANT_API_TOKEN"]
    supplied = request.headers.get("X-Plant-Token", "")
    if not supplied or supplied != expected:
        abort(403)


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/api/state")
def state():
    require_token()
    return jsonify(model.snapshot())


@app.post("/api/actuators")
def actuators():
    require_token()
    body = request.get_json(silent=True) or {}
    try:
        result = model.set_actuators(str(body.get("component", "")), body.get("values", {}))
    except (TypeError, ValueError) as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(result)


@app.post("/api/reset")
def reset():
    require_token()
    return jsonify(model.reset())


def physics_loop() -> None:
    previous = time.monotonic()
    while True:
        time.sleep(0.1)
        current = time.monotonic()
        model.tick(current - previous)
        previous = current


if __name__ == "__main__":
    threading.Thread(target=physics_loop, name="physics-loop", daemon=True).start()
    serve(app, host="0.0.0.0", port=8000, threads=4)

