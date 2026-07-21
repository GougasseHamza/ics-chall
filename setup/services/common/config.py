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


class PLC2Holding(IntEnum):
    CONVEYOR_MODE = 0
    RESET_COMMAND = 1


class PLC2Input(IntEnum):
    BOTTLE_LEVEL = 0
    BOTTLE_POSITION = 1
    CONVEYOR_STATUS = 2
    GOOD_BOTTLES = 3
    REJECTED_BOTTLES = 4
    SPILL_ALARM = 5


class RIOHolding(IntEnum):
    LEVEL_CALIBRATION_BIAS = 0


class RIOInput(IntEnum):
    REPORTED_TANK_LEVEL = 0
    SENSOR_QUALITY = 1


PLC1_HOST = "172.30.10.11"
PLC2_HOST = "172.30.10.12"
RIO_HOST = "172.30.10.13"
PLANT_URL = "http://plant:8000"
MODBUS_PORT = 502


def clamp_register(value: float) -> int:
    """Convert a numeric value to an unsigned 16-bit register."""
    return max(0, min(65535, int(round(value))))
