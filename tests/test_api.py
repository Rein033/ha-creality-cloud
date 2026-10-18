"""parse_device and the command allow-list, without network."""
import pytest

from custom_components.creality_cloud.api import COMMANDS, CrealityCloud, parse_device


def _attr(device, **values):
    for a in device["iotAttr"]:
        if a["key"] in values:
            a["value"] = values[a["key"]]
    return device


def test_printing(device):
    p = parse_device(device)
    assert p.online
    assert p.state == "printing"
    assert p.active
    assert p.progress == device["printInfo"]["printProgress"]
    assert p.remaining == device["printInfo"]["printLeftTime"]
    assert p.nozzle == float(device["nozzleTemp"])
    assert p.chamber == float(device["boxTemp"])
    assert p.light is True
    assert p.thumbnail.startswith("https://pic2-cdn.creality.com/")
    assert p.error is None


def test_idle_hides_job(device):
    p = parse_device(_attr(device, state=0))
    assert p.state == "idle"
    assert p.job is None and p.progress is None and p.thumbnail is None


def test_paused_and_offline(device):
    assert parse_device(_attr(device, state=5)).state == "paused"
    assert parse_device(_attr(device, connect=0)).online is False


def test_foreign_thumbnail_dropped(device):
    device["printInfo"]["gcodeThumbnail"] = "https://example.com/x.png"
    assert parse_device(device).thumbnail is None


def test_only_fixed_commands():
    assert set(COMMANDS) == {"pause", "resume", "cancel", "light_on", "light_off"}


async def test_unknown_command_refused(device):
    cloud = CrealityCloud(None, "a@b.c", "x")
    with pytest.raises(ValueError):
        await cloud.command(parse_device(device), "gcode")


def test_parse_job():
    from custom_components.creality_cloud.api import parse_job

    assert parse_job("Skull_bowl_widened.stl_PLA_8h35m17s.gcode") == {
        "file_name": "Skull_bowl_widened.stl_PLA_8h35m17s.gcode", "filament_types": ["PLA"], "slicer_estimate": 30917}
    j = parse_job("Bracket_PETG_0.16_1d2h3m.gcode")
    assert j["filament_types"] == ["PETG"] and j["layer_height"] == 0.16 and j["slicer_estimate"] == 93780
    assert parse_job("plain.gcode") == {"file_name": "plain.gcode"}
    assert parse_job(None) == {}
