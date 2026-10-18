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



def test_events_between(printers):
    from custom_components.creality_cloud.coordinator import events_between
    p = list(printers.values())[0]
    mk = lambda **kw: type(p)(**{**p.__dict__, **kw})
    assert events_between(None, p) == []
    assert events_between(mk(state="printing"), mk(state="finished")) == ["finished"]
    assert events_between(mk(state="idle"), mk(state="printing")) == ["started"]
    assert events_between(mk(state="paused"), mk(state="printing")) == []
    assert events_between(mk(online=True), mk(online=False)) == ["offline"]
    assert events_between(mk(error=None), mk(error=301)) == ["error"]


def test_records_and_timelapse():
    from custom_components.creality_cloud.api import attach_timelapses, parse_record
    r = parse_record({"id": "a", "name": "x.gcode", "printState": 2, "printStartTime": 10, "printEndTime": 70,
                      "printJobTime": 0, "thumbnailUrl": "https://pic2-cdn.creality.com/t", "tfCard": True, "timelapseId": "v1"})
    assert (r.state, r.duration, r.on_printer, r.timelapse_id) == ("finished", 60, True, "v1")
    attach_timelapses([r], [{"id": "v1", "videoUrl": "https://video-cdn.creality.com/v.mp4", "coverUrl": "https://evil.example/c.png"}])
    assert r.timelapse == "https://video-cdn.creality.com/v.mp4" and r.timelapse_cover is None


def test_media_url_only_creality():
    from custom_components.creality_cloud.api import media_url
    assert media_url("https://pic2-cdn.creality.com/x") and media_url("https://x.crealitycloud.cn/y")
    for bad in ("http://pic2-cdn.creality.com/x", "https://creality.com.evil.io/x", "javascript:alert(1)", None, 3):
        assert media_url(bad) is None


def test_latest_firmware():
    from custom_components.creality_cloud.api import latest_firmware
    ota = [{"hardwareVer": "HW1", "otaVer": "1.3.5.22"}, {"hardwareVer": "HW1", "otaVer": "1.3.10.1"}, {"hardwareVer": "HW2", "otaVer": "9.9"}]
    assert latest_firmware(ota, "HW1") == "1.3.10.1"
    assert latest_firmware(ota, "HW3") is None and latest_firmware(ota, None) is None


def test_reprint_only_plain_gcode_names():
    from custom_components.creality_cloud.api import reprint_params
    assert reprint_params("Benchy v2.gcode") == {"opGcodeFile": "printprt:/usr/data/printer_data/gcodes/Benchy v2.gcode"}
    for bad in ("../../etc/passwd.gcode", "a/b.gcode", "x.sh", "", "evil\nname.gcode"):
        with pytest.raises(ValueError):
            reprint_params(bad)


def test_hardware_version(device):
    assert parse_device(device).hardware == "CR4CU220812S11"
