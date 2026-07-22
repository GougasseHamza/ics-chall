"""Shared register maps and challenge configuration.

Addresses in this module are zero-based offsets as used by Modbus libraries.
Documentation presents them in the familiar 30001/40001 notation.
"""

from enum import IntEnum


SCALE_PERCENT = 100
SCALE_TEMPERATURE = 10
SCALE_SECONDS = 10


class Mode(IntEnum):
    MANUAL_OFF = 1
    MANUAL_ON = 2
    AUTO = 3


class MachineState(IntEnum):
    RUNNING = 0
    WARNING = 1
    TRIPPED = 2
    BROKEN = 3


class PLC1Holding(IntEnum):
    INLET_MODE = 0
    PUMP_MODE = 1
    LOW_SETPOINT = 2
    HIGH_SETPOINT = 3
    RESET_COMMAND = 4
    CONVEYOR_MODE = 5


class PLC1Input(IntEnum):
    TANK_LEVEL = 0
    INLET_STATUS = 1
    PUMP_STATUS = 2
    PUMP_TEMPERATURE = 3
    PUMP_VIBRATION = 4
    DRY_RUN_SECONDS = 5
    PUMP_DAMAGE = 6
    LOW_LEVEL_ALARM = 7
    DRY_RUN_ALARM = 8
    MACHINE_STATE = 9
    BOTTLE_LEVEL = 10
    BOTTLE_POSITION = 11
    CONVEYOR_STATUS = 12
    GOOD_BOTTLES = 13
    REJECTED_BOTTLES = 14
    SPILL_ALARM = 15


class RIOHolding(IntEnum):
    LEVEL_CALIBRATION_BIAS = 0


class RIOInput(IntEnum):
    REPORTED_TANK_LEVEL = 0
    SENSOR_QUALITY = 1


PLC1_HOST = "172.30.10.11"
RIO_HOST = "172.30.10.13"
PLANT_URL = "http://plant:8000"
MODBUS_PORT = 502


def clamp_register(value: float) -> int:
    """Convert a numeric value to an unsigned 16-bit register."""
    return max(0, min(65535, int(round(value))))
