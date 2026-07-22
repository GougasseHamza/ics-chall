from services.common.config import MachineState
from services.plant.model import PlantModel


def advance(model: PlantModel, seconds: float, step: float = 0.1) -> None:
    for _ in range(int(seconds / step)):
        model.tick(step)


def test_known_safe_initial_state():
    state = PlantModel().snapshot()
    assert state["tank_level"] == 68.0
    assert state["machine_state"] == int(MachineState.RUNNING)
    assert state["pump_damage"] == 0.0


def test_sustained_dry_running_breaks_pump():
    model = PlantModel()
    model.set_actuators("plc1", {"inlet_open": False, "pump_running": True})
    advance(model, 50.0)
    state = model.snapshot()
    assert state["tank_level"] == 0.0
    assert state["dry_run_seconds"] >= model.DAMAGE_START_SECONDS
    assert state["pump_damage"] == model.BREAK_DAMAGE
    assert state["machine_state"] == int(MachineState.BROKEN)
    assert state["pump_running"] is False


def test_short_dry_event_does_not_break_pump():
    model = PlantModel()
    model._state.tank_level = 0.0
    model.set_actuators("plc1", {"inlet_open": False, "pump_running": True})
    advance(model, 4.0)
    model.set_actuators("plc1", {"inlet_open": True, "pump_running": False})
    advance(model, 3.0)
    state = model.snapshot()
    assert state["pump_damage"] == 0.0
    assert state["machine_state"] != int(MachineState.BROKEN)


def test_component_cannot_write_an_unknown_actuator():
    model = PlantModel()
    try:
        model.set_actuators("plc1", {"unknown_output": True})
    except ValueError as exc:
        assert "unsupported actuator" in str(exc)
    else:
        raise AssertionError("unknown actuator write was accepted")


def test_reset_recovers_terminal_failure():
    model = PlantModel()
    model._state.machine_state = int(MachineState.BROKEN)
    model._state.pump_damage = 100.0
    state = model.reset()
    assert state["machine_state"] == int(MachineState.RUNNING)
    assert state["pump_damage"] == 0.0
