"""Deterministic bottling-line physics model used by the CTF.

The model is intentionally simple enough to audit while preserving the
important cyber-physical relationship: a network write falsifies a sensor
value, the PLC changes an actuator based on that value, and the actuator
changes physical state over time.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import RLock

from services.common.config import MachineState


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PlantState:
    tank_level: float = 68.0
    inlet_open: bool = True
    pump_running: bool = False
    pump_temperature: float = 38.0
    pump_vibration: float = 1.2
    dry_run_seconds: float = 0.0
    pump_damage: float = 0.0
    low_level_alarm: bool = False
    dry_run_alarm: bool = False
    machine_state: int = int(MachineState.RUNNING)
    bottle_level: float = 0.0
    bottle_position: float = 0.0
    conveyor_running: bool = False
    good_bottles: int = 0
    rejected_bottles: int = 0
    spill_alarm: bool = False
    updated_at: str = ""


class PlantModel:
    INLET_RATE = 1.7
    PUMP_DRAIN_RATE = 2.9
    BOTTLE_FILL_RATE = 30.0
    CONVEYOR_RATE = 30.0
    DRY_LEVEL = 0.5
    DRY_ALARM_SECONDS = 3.0
    DAMAGE_START_SECONDS = 9.0
    BREAK_DAMAGE = 100.0

    def __init__(self) -> None:
        self._lock = RLock()
        self._events: deque[dict[str, str]] = deque(maxlen=80)
        self._state = PlantState(updated_at=utc_now())
        self._last_flags: dict[str, bool] = {}
        self._event("INFO", "Line 4 process simulation started")

    def _event(self, severity: str, message: str) -> None:
        self._events.appendleft({"time": utc_now(), "severity": severity, "message": message})

    def reset(self) -> dict:
        with self._lock:
            self._state = PlantState(updated_at=utc_now())
            self._events.clear()
            self._last_flags.clear()
            self._event("INFO", "Plant reset to a known-safe state")
            return self.snapshot()

    def set_actuators(self, component: str, values: dict) -> dict:
        allowed = {
            "plc1": {"inlet_open", "pump_running"},
            "plc2": {"conveyor_running"},
        }
        if component not in allowed:
            raise ValueError("unknown actuator component")
        unexpected = set(values) - allowed[component]
        if unexpected:
            raise ValueError(f"unsupported actuator(s): {', '.join(sorted(unexpected))}")

        with self._lock:
            for key, value in values.items():
                setattr(self._state, key, bool(value))
            return self.snapshot()

    @staticmethod
    def _approach(current: float, target: float, maximum_delta: float) -> float:
        if current < target:
            return min(target, current + maximum_delta)
        return max(target, current - maximum_delta)

    def _transition_event(self, name: str, active: bool, severity: str, on_message: str, off_message: str) -> None:
        previous = self._last_flags.get(name, False)
        if active and not previous:
            self._event(severity, on_message)
        elif previous and not active:
            self._event("INFO", off_message)
        self._last_flags[name] = active

    def tick(self, dt: float) -> None:
        dt = max(0.0, min(float(dt), 0.5))
        if dt == 0:
            return

        with self._lock:
            s = self._state

            if s.machine_state == int(MachineState.BROKEN):
                s.pump_running = False

            if s.inlet_open:
                s.tank_level += self.INLET_RATE * dt

            if s.pump_running and s.tank_level > 0:
                transfer = min(s.tank_level, self.PUMP_DRAIN_RATE * dt)
                s.tank_level -= transfer
                # The filler has a short downstream drip zone. This prevents
                # the normal PLC scan overlap between pump stop and conveyor
                # start from producing a nuisance spill alarm.
                if s.bottle_position <= 25.0:
                    s.bottle_level = min(130.0, s.bottle_level + self.BOTTLE_FILL_RATE * dt)
                else:
                    s.spill_alarm = True

            s.tank_level = max(0.0, min(100.0, s.tank_level))

            if s.conveyor_running:
                s.bottle_position += self.CONVEYOR_RATE * dt
                if s.bottle_position >= 100.0:
                    if 95.0 <= s.bottle_level <= 105.0:
                        s.good_bottles += 1
                    else:
                        s.rejected_bottles += 1
                    s.bottle_position %= 100.0
                    s.bottle_level = 0.0
                    s.spill_alarm = False

            is_dry = s.pump_running and s.tank_level <= self.DRY_LEVEL
            if is_dry:
                s.dry_run_seconds += dt
                s.pump_temperature += 8.5 * dt
                s.pump_vibration = min(30.0, s.pump_vibration + 1.1 * dt)
                if s.dry_run_seconds >= self.DAMAGE_START_SECONDS:
                    s.pump_damage = min(self.BREAK_DAMAGE, s.pump_damage + 17.0 * dt)
            else:
                # Preserve the terminal dry-run duration as incident evidence.
                # During a recoverable event it decays normally once flow is
                # restored or the pump is stopped.
                if s.machine_state != int(MachineState.BROKEN):
                    s.dry_run_seconds = max(0.0, s.dry_run_seconds - 2.5 * dt)
                target_temp = 52.0 if s.pump_running else 34.0
                s.pump_temperature = self._approach(s.pump_temperature, target_temp, 2.5 * dt)
                s.pump_vibration = self._approach(s.pump_vibration, 2.0 if s.pump_running else 1.2, 1.8 * dt)

            s.low_level_alarm = s.tank_level <= 5.0
            s.dry_run_alarm = s.dry_run_seconds >= self.DRY_ALARM_SECONDS

            if s.pump_damage >= self.BREAK_DAMAGE:
                if s.machine_state != int(MachineState.BROKEN):
                    self._event("CRITICAL", "P-101 seized after sustained dry running")
                s.machine_state = int(MachineState.BROKEN)
                s.pump_running = False
            elif s.dry_run_alarm or s.spill_alarm:
                s.machine_state = int(MachineState.WARNING)
            else:
                s.machine_state = int(MachineState.RUNNING)

            self._transition_event(
                "low_level",
                s.low_level_alarm,
                "WARNING",
                "TK-101 low-level alarm active",
                "TK-101 level returned to the normal range",
            )
            self._transition_event(
                "dry_run",
                s.dry_run_alarm,
                "CRITICAL",
                "P-101 dry-run condition detected",
                "P-101 dry-run condition cleared",
            )
            self._transition_event(
                "spill",
                s.spill_alarm,
                "WARNING",
                "Filler flow detected outside the bottle-fill window",
                "Filler spill condition cleared",
            )
            s.updated_at = utc_now()

    def snapshot(self) -> dict:
        with self._lock:
            result = asdict(self._state)
            result["events"] = deepcopy(list(self._events))
            return result
