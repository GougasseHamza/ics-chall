from services.common.config import PLC1Holding, PLC1Input, RIOHolding, RIOInput
from services.rio.app import RIO101, signed_register


def test_register_offsets_are_stable():
    assert int(PLC1Holding.PUMP_MODE) == 1
    assert int(PLC1Input.MACHINE_STATE) == 9
    assert int(PLC1Holding.CONVEYOR_MODE) == 5
    assert int(PLC1Input.BOTTLE_LEVEL) == 10
    assert int(PLC1Input.SPILL_ALARM) == 15
    assert int(RIOHolding.LEVEL_CALIBRATION_BIAS) == 0
    assert int(RIOInput.REPORTED_TANK_LEVEL) == 0


def test_modbus_register_signed_conversion():
    assert signed_register(0) == 0
    assert signed_register(10000) == 10000
    assert signed_register(0xFFFF) == -1
    assert signed_register(0x8000) == -32768


def test_rio_register_map_is_small_and_self_identifying():
    rio = RIO101()
    assert rio.server.data_bank.get_holding_registers(0, 1) == [0]
    assert rio.server.data_bank.get_holding_registers(1, 1) is None
    assert rio.server.data_bank.get_input_registers(0, 2) == [0, 0]
    assert rio.server.data_bank.get_input_registers(2, 1) is None
    assert rio.server.device_id.vendor_name == b"Rivermark Beverage Co."
    assert rio.server.device_id.product_code == b"RIO101"
    assert rio.server.device_id.product_name == b"LT-101 Remote I/O Gateway"
