"""PLC-101: integrated tank, transfer-pump and conveyor controller."""

from __future__ import annotations

import logging
import time

from pyModbusTCP.client import ModbusClient
from pyModbusTCP.server import DataBank, DeviceIdentification, ModbusServer

from services.common.config import (
    MachineState,
    Mode,
    PLC1Holding,
    PLC1Input,
    RIO_HOST,
    RIOInput,
    SCALE_PERCENT,
    SCALE_SECONDS,
    SCALE_TEMPERATURE,
    clamp_register,
)
from services.common.http import get_plant_state, reset_plant, set_actuators


logging.basicConfig(level=logging.INFO, format="%(asctime)s PLC-101 %(levelname)s %(message)s")
LOG = logging.getLogger("plc101")


class PLC101:
    SCAN_SECONDS = 0.20
    RESET_MAGIC = 0xA55A

    def __init__(self) -> None:
        data_bank = DataBank(
            coils_size=0,
            d_inputs_size=0,
            h_regs_size=6,
            i_regs_size=16,
        )
        device_id = DeviceIdentification(
            vendor_name=b"Rivermark Beverage Co.",
            product_code=b"PLC101",
            major_minor_revision=b"4.7",
            product_name=b"Integrated Bottling Cell Controller",
            model_name=b"U-PLC 1200",
            user_application_name=b"Line 4 PLC-101",
        )
        self.server = ModbusServer(
            host="0.0.0.0",
            port=502,
            no_block=True,
            data_bank=data_bank,
            device_id=device_id,
        )
        self.rio = ModbusClient(
            host=RIO_HOST,
            port=502,
            auto_open=True,
            auto_close=True,
            timeout=1.0,
        )
        self.inlet_output = True
        self.pump_output = False
        self.conveyor_output = False

    def start(self) -> None:
        self.server.start()
        self.server.data_bank.set_holding_registers(
            0,
            [
                int(Mode.AUTO),
                int(Mode.AUTO),
                2500,
                8500,
                0,
                int(Mode.AUTO),
            ],
        )
        LOG.info("Modbus/TCP server listening on port 502")
        while True:
            started = time.monotonic()
            try:
                self.scan()
            except Exception:
                LOG.exception("control scan failed; commanding safe outputs")
                self.inlet_output = False
                self.pump_output = False
                self.conveyor_output = False
                try:
                    set_actuators(
                        "plc1",
                        {"inlet_open": False, "pump_running": False, "conveyor_running": False},
                    )
                except Exception:
                    pass
            remaining = self.SCAN_SECONDS - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    def _holding(self, address: PLC1Holding, default: int) -> int:
        values = self.server.data_bank.get_holding_registers(int(address), 1)
        return int(values[0]) if values else default

    def _reported_tank_level(self) -> float:
        values = self.rio.read_input_registers(int(RIOInput.REPORTED_TANK_LEVEL), 1)
        if values is None or len(values) != 1:
            raise ConnectionError("LT-101 remote I/O did not return a level reading")
        return int(values[0]) / SCALE_PERCENT

    @staticmethod
    def _mode(value: int) -> Mode | None:
        try:
            return Mode(value)
        except ValueError:
            return None

    def scan(self) -> None:
        state = get_plant_state()
        reported_tank_level = self._reported_tank_level()
        inlet_mode = self._mode(self._holding(PLC1Holding.INLET_MODE, int(Mode.AUTO)))
        pump_mode = self._mode(self._holding(PLC1Holding.PUMP_MODE, int(Mode.AUTO)))
        conveyor_mode = self._mode(self._holding(PLC1Holding.CONVEYOR_MODE, int(Mode.AUTO)))
        low = self._holding(PLC1Holding.LOW_SETPOINT, 2500) / SCALE_PERCENT
        high = self._holding(PLC1Holding.HIGH_SETPOINT, 8500) / SCALE_PERCENT

        if self._holding(PLC1Holding.RESET_COMMAND, 0) == self.RESET_MAGIC:
            state = reset_plant()
            self.server.data_bank.set_holding_registers(int(PLC1Holding.RESET_COMMAND), [0])
            LOG.warning("process reset requested through maintenance register")

        if inlet_mode == Mode.MANUAL_OFF:
            self.inlet_output = False
        elif inlet_mode == Mode.MANUAL_ON:
            self.inlet_output = True
        elif inlet_mode == Mode.AUTO:
            if reported_tank_level <= low:
                self.inlet_output = True
            elif reported_tank_level >= high:
                self.inlet_output = False
        else:
            self.inlet_output = False

        if pump_mode == Mode.MANUAL_OFF:
            self.pump_output = False
        elif pump_mode == Mode.MANUAL_ON:
            # The low-level permissive applies in every mode. The intended
            # vulnerability is false input data over unauthenticated Modbus,
            # not a missing safety branch in this control program.
            self.pump_output = bool(
                reported_tank_level > 5.0
                and state["machine_state"] != int(MachineState.BROKEN)
            )
        elif pump_mode == Mode.AUTO:
            bottle_in_position = state["bottle_position"] <= 12.0
            needs_product = state["bottle_level"] < 98.0
            self.pump_output = bool(
                bottle_in_position
                and needs_product
                and reported_tank_level > 5.0
                and state["machine_state"] != int(MachineState.BROKEN)
            )
        else:
            self.pump_output = False

        if state["machine_state"] == int(MachineState.BROKEN):
            self.pump_output = False

        if conveyor_mode == Mode.MANUAL_OFF:
            self.conveyor_output = False
        elif conveyor_mode == Mode.MANUAL_ON:
            self.conveyor_output = True
        elif conveyor_mode == Mode.AUTO:
            self.conveyor_output = state["bottle_level"] >= 98.0
        else:
            self.conveyor_output = False

        updated = set_actuators(
            "plc1",
            {
                "inlet_open": self.inlet_output,
                "pump_running": self.pump_output,
                "conveyor_running": self.conveyor_output,
            },
        )
        self.server.data_bank.set_input_registers(
            0,
            [
                clamp_register(reported_tank_level * SCALE_PERCENT),
                int(updated["inlet_open"]),
                int(updated["pump_running"]),
                clamp_register(updated["pump_temperature"] * SCALE_TEMPERATURE),
                clamp_register(updated["pump_vibration"] * SCALE_TEMPERATURE),
                clamp_register(updated["dry_run_seconds"] * SCALE_SECONDS),
                clamp_register(updated["pump_damage"] * SCALE_PERCENT),
                int(reported_tank_level <= 5.0),
                int(updated["dry_run_alarm"]),
                int(updated["machine_state"]),
                clamp_register(updated["bottle_level"] * SCALE_PERCENT),
                clamp_register(updated["bottle_position"] * SCALE_PERCENT),
                int(updated["conveyor_running"]),
                clamp_register(updated["good_bottles"]),
                clamp_register(updated["rejected_bottles"]),
                int(updated["spill_alarm"]),
            ],
        )


if __name__ == "__main__":
    PLC101().start()
