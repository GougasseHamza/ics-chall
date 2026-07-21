"""Remote I/O gateway for the LT-101 tank level transmitter.

The gateway exposes the measured level and its maintenance calibration bias
over legacy Modbus/TCP. Classic Modbus has no client authentication or message
integrity, so any host on the trusted control VLAN can alter the bias. PLC-101
then receives a plausible but false process value while the physical model
continues to track the real level independently.
"""

from __future__ import annotations

import logging
import time

from pyModbusTCP.server import DataBank, DeviceIdentification, ModbusServer

from services.common.config import RIOHolding, SCALE_PERCENT, clamp_register
from services.common.http import get_plant_state


logging.basicConfig(level=logging.INFO, format="%(asctime)s RIO-101 %(levelname)s %(message)s")
LOG = logging.getLogger("rio101")


def signed_register(value: int) -> int:
    """Interpret one unsigned Modbus register as a signed 16-bit value."""
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


class RIO101:
    SCAN_SECONDS = 0.20

    def __init__(self) -> None:
        data_bank = DataBank(
            coils_size=0,
            d_inputs_size=0,
            h_regs_size=1,
            i_regs_size=2,
        )
        device_id = DeviceIdentification(
            vendor_name=b"Rivermark Beverage Co.",
            product_code=b"RIO101",
            major_minor_revision=b"4.7",
            product_name=b"LT-101 Remote I/O Gateway",
            model_name=b"RIO-100",
            user_application_name=b"Line 4 Tank Level",
        )
        self.server = ModbusServer(
            host="0.0.0.0",
            port=502,
            no_block=True,
            data_bank=data_bank,
            device_id=device_id,
        )

    def start(self) -> None:
        self.server.start()
        self.server.data_bank.set_holding_registers(
            int(RIOHolding.LEVEL_CALIBRATION_BIAS),
            [0],
        )
        LOG.info("LT-101 Modbus/TCP remote I/O listening on port 502")
        while True:
            started = time.monotonic()
            try:
                self.scan()
            except Exception:
                LOG.exception("remote I/O scan failed")
                self.server.data_bank.set_input_registers(0, [0, 0])
            remaining = self.SCAN_SECONDS - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    def scan(self) -> None:
        state = get_plant_state()
        values = self.server.data_bank.get_holding_registers(
            int(RIOHolding.LEVEL_CALIBRATION_BIAS),
            1,
        )
        bias = signed_register(int(values[0]) if values else 0)
        measured = clamp_register(state["tank_level"] * SCALE_PERCENT)
        # A real 4-20 mA level transmitter is bounded by its configured span.
        # Saturating the output keeps malicious calibration plausible on HMI
        # screens instead of producing an obvious value above 100 percent.
        reported = max(0, min(100 * SCALE_PERCENT, measured + bias))
        self.server.data_bank.set_input_registers(0, [reported, 1])


if __name__ == "__main__":
    RIO101().start()
