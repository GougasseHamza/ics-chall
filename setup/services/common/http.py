"""Small helpers for authenticated communication with the physics service."""

from __future__ import annotations

import os
from typing import Any

import requests

from services.common.config import PLANT_URL


def _headers() -> dict[str, str]:
    return {"X-Plant-Token": os.environ["PLANT_API_TOKEN"]}


def get_plant_state(timeout: float = 1.0) -> dict[str, Any]:
    response = requests.get(f"{PLANT_URL}/api/state", headers=_headers(), timeout=timeout)
    response.raise_for_status()
    return response.json()


def set_actuators(component: str, values: dict[str, Any], timeout: float = 1.0) -> dict[str, Any]:
    response = requests.post(
        f"{PLANT_URL}/api/actuators",
        headers=_headers(),
        json={"component": component, "values": values},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def reset_plant(timeout: float = 2.0) -> dict[str, Any]:
    response = requests.post(f"{PLANT_URL}/api/reset", headers=_headers(), timeout=timeout)
    response.raise_for_status()
    return response.json()

