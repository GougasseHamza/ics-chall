import json
from pathlib import Path
from xml.etree import ElementTree


SETUP_ROOT = Path(__file__).resolve().parents[1]
FUXA_ROOT = SETUP_ROOT / "services" / "fuxa"


def load_project():
    return json.loads((FUXA_ROOT / "project.json").read_text())


def test_animation_actions_follow_plc_status_tags():
    items = load_project()["hmi"]["views"][0]["items"]

    expected = {
        "MTR_pump": "plc101_pump_running",
        "MTR_conveyor": "plc102_conveyor_running",
        "PIE_conveyor": "plc102_conveyor_running",
    }
    for item_id, variable_id in expected.items():
        actions = items[item_id]["property"]["actions"]
        assert {(action["type"], action["range"]["min"], action["range"]["max"]) for action in actions} == {
            ("clockwise", 1, 1),
            ("stop", 0, 0),
        }
        assert {action["variableId"] for action in actions} == {variable_id}


def test_bottle_and_tank_progress_gauges_have_native_fuxa_structure():
    items = load_project()["hmi"]["views"][0]["items"]
    assert items["GXP_bottle_fill"]["property"]["variableId"] == "plc102_bottle_level"
    assert items["GXP_tank"]["property"]["variableId"] == "plc101_tank_level"

    root = ElementTree.parse(FUXA_ROOT / "line4.svg").getroot()
    by_id = {element.attrib.get("id"): element for element in root.iter() if element.attrib.get("id")}

    for gauge_id in ("GXP_bottle_fill", "GXP_tank"):
        gauge = by_id[gauge_id]
        children = list(gauge)
        assert len(children) == 3
        child_ids = {child.attrib["id"] for child in children}
        assert any(item.startswith("A-GXP_") for item in child_ids)
        assert any(item.startswith("B-GXP_") for item in child_ids)
        assert any(item.startswith("H-GXP_") for item in child_ids)
