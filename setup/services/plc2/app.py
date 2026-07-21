"""PLC-102: bottle conveyor controller."""

from __future__ import annotations

import logging
import time

from pyModbusTCP.server import DataBank, DeviceIdentification, ModbusServer

from services.common.config import Mode, PLC2Holding, SCALE_PERCENT, clamp_register
from services.common.http import get_plant_state, set_actuators


logging.basicConfig(level=logging.INFO, format="%(asctime)s PLC-102 %(levelname)s %(message)s")
LOG = logging.getLogger("plc102")


class PLC102:
    SCAN_SECONDS = 0.20

    def __init__(self) -> None:
        data_bank = DataBank(
            coils_size=0,
            d_inputs_size=0,
            h_regs_size=2,
            i_regs_size=6,
        )
        device_id = DeviceIdentification(
            vendor_name=b"Rivermark Beverage Co.",
            product_code=b"PLC102",
            major_minor_revision=b"4.7",
            product_name=b"Bottle Conveyor Controller",
            model_name=b"U-PLC 1200",
            user_application_name=b"Line 4 PLC-102",
        )
        self.server = ModbusServer(
            host="0.0.0.0",
            port=502,
            no_block=True,
            data_bank=data_bank,
            device_id=device_id,
        )
        self.conveyor_output = False

    def start(self) -> None:
        self.server.start()
        self.server.data_bank.set_holding_registers(0, [int(Mode.AUTO), 0])
        LOG.info("Modbus/TCP server listening on port 502")
        while True:
            started = time.monotonic()
            try:
                self.scan()
            except Exception:
                LOG.exception("control scan failed; stopping conveyor")
                self.conveyor_output = False
                try:
                    set_actuators("plc2", {"conveyor_running": False})
                except Exception:
                    pass
            remaining = self.SCAN_SECONDS - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    def scan(self) -> None:
        state = get_plant_state()
        values = self.server.data_bank.get_holding_registers(int(PLC2Holding.CONVEYOR_MODE), 1)
        raw_mode = int(values[0]) if values else int(Mode.AUTO)
        try:
            mode = Mode(raw_mode)
        except ValueError:
            mode = None

        if mode == Mode.MANUAL_OFF:
            self.conveyor_output = False
        elif mode == Mode.MANUAL_ON:
            self.conveyor_output = True
        elif mode == Mode.AUTO:
            self.conveyor_output = state["bottle_level"] >= 98.0
        else:
            self.conveyor_output = False

        updated = set_actuators("plc2", {"conveyor_running": self.conveyor_output})
        self.server.data_bank.set_input_registers(
            0,
            [
                clamp_register(updated["bottle_level"] * SCALE_PERCENT),
                clamp_register(updated["bottle_position"] * SCALE_PERCENT),
                int(updated["conveyor_running"]),
                clamp_register(updated["good_bottles"]),
                clamp_register(updated["rejected_bottles"]),
                int(updated["spill_alarm"]),
            ],
        )


if __name__ == "__main__":
    PLC102().start()
