"""Config flow, entities and commands inside a real Home Assistant test instance (cloud mocked)."""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.creality_cloud.api import CrealityAuthError, PrintRecord
from custom_components.creality_cloud.const import CONF_TOKEN, DOMAIN

API = "custom_components.creality_cloud.api.CrealityCloud."
TOKEN = {"token": "t", "uid": 1}
HISTORY = [PrintRecord("r2", "Benchy.stl_PLA_1h2m3s.gcode", "finished", 100, 3823, 3723, None, True, None),
           PrintRecord("r1", "Old.gcode", "stopped", 1, 50, 49, None, False, None)]


async def _setup(hass, printers):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="a@b.c", title="a@b.c",
                            data={CONF_EMAIL: "a@b.c", CONF_PASSWORD: "pw", CONF_TOKEN: TOKEN})
    entry.add_to_hass(hass)
    with patch(API + "printers", AsyncMock(return_value=printers)), \
            patch(API + "history", AsyncMock(return_value=HISTORY)), \
            patch(API + "latest_firmware", AsyncMock(return_value="1.3.6.1")):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _eid(hass, platform, key):
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, "TESTDEVICE_" + key)


async def test_config_flow(hass, printers):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert r["type"] is FlowResultType.FORM
    with patch(API + "login", AsyncMock(return_value=TOKEN)), patch(API + "printers", AsyncMock(return_value=printers)):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"region": "international", CONF_EMAIL: " A@B.c ", CONF_PASSWORD: "pw"})
        await hass.async_block_till_done()
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["title"] == "a@b.c"
    assert r["data"] == {"region": "international", CONF_EMAIL: "a@b.c", CONF_PASSWORD: "pw", CONF_TOKEN: TOKEN}


async def test_config_flow_wrong_password(hass):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(API + "login", AsyncMock(side_effect=CrealityAuthError("nope"))):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"region": "international", CONF_EMAIL: "a@b.c", CONF_PASSWORD: "x"})
    assert r["type"] is FlowResultType.FORM
    assert r["errors"] == {"base": "invalid_auth"}


async def test_entities(hass, printers, device):
    await _setup(hass, printers)
    assert hass.states.get(_eid(hass, "sensor", "status")).state == "printing"
    assert float(hass.states.get(_eid(hass, "sensor", "progress")).state) == device["printInfo"]["printProgress"]
    assert float(hass.states.get(_eid(hass, "sensor", "nozzle_temperature")).state) == float(device["nozzleTemp"])
    assert hass.states.get(_eid(hass, "binary_sensor", "online")).state == "on"
    assert hass.states.get(_eid(hass, "light", "light")).state == "on"
    assert hass.states.get(_eid(hass, "button", "pause")).state != "unavailable"
    assert hass.states.get(_eid(hass, "button", "resume")).state == "unavailable"
    assert hass.states.get(_eid(hass, "image", "thumbnail")) is not None


async def test_commands(hass, printers):
    await _setup(hass, printers)
    with patch(API + "command", AsyncMock()) as cmd, patch(API + "printers", AsyncMock(return_value=printers)):
        await hass.services.async_call("button", "press", {"entity_id": _eid(hass, "button", "pause")}, blocking=True)
        await hass.services.async_call("light", "turn_off", {"entity_id": _eid(hass, "light", "light")}, blocking=True)
    assert [c.args[1] for c in cmd.call_args_list] == ["pause", "light_off"]


async def test_auth_failure_starts_reauth(hass, printers):
    entry = await _setup(hass, printers)
    with patch(API + "printers", AsyncMock(side_effect=CrealityAuthError("expired"))):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)


async def test_card_is_served(hass, hass_client, printers):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    await _setup(hass, printers)
    client = await hass_client()
    r = await client.get("/creality_cloud/creality-print-card.js")
    assert r.status == 200
    text = await r.text()
    assert "define('creality-print-card', CrealityPrintCard)" in text and "creality-print-group-card" in text


async def test_diagnostics_hide_secrets(hass, printers):
    from custom_components.creality_cloud.diagnostics import async_get_config_entry_diagnostics

    entry = await _setup(hass, printers)
    text = str(await async_get_config_entry_diagnostics(hass, entry))
    for secret in ("a@b.c", "pw", "TESTDEVICE", "TEST-SN", "000000000000", "00000000-test-tbid", "192.0.2.10", "K1Max-TEST"):
        assert secret not in text, secret
    assert "printing" in text



async def test_new_entities(hass, printers):
    await _setup(hass, printers)
    last = hass.states.get(_eid(hass, "sensor", "last_print"))
    assert last.state == "Benchy.stl_PLA_1h2m3s.gcode"
    assert [h["id"] for h in last.attributes["history"]] == ["r2", "r1"]
    fw = hass.states.get(_eid(hass, "update", "firmware"))
    assert fw.state == "on" and fw.attributes["latest_version"] == "1.3.6.1"
    # printer is printing, so printing again is not possible
    assert hass.states.get(_eid(hass, "button", "reprint_last")).state == "unavailable"


async def test_reprint_service(hass, printers, device):
    from homeassistant.helpers import device_registry as dr
    from homeassistant.exceptions import HomeAssistantError

    await _setup(hass, printers)
    dev = dr.async_get(hass).async_get(er.async_get(hass).async_get(_eid(hass, "sensor", "status")).device_id)
    with patch(API + "_rpc", AsyncMock()) as rpc, patch(API + "printers", AsyncMock(return_value=printers)):
        try:
            await hass.services.async_call(DOMAIN, "reprint", {"device_id": dev.id, "file_name": "Benchy.gcode"}, blocking=True)
            raised = False
        except HomeAssistantError:
            raised = True
    assert raised and rpc.call_count == 0   # busy printer: refused
    idle = {k: type(v)(**{**v.__dict__, "state": "idle", "progress": None}) for k, v in printers.items()}
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    entry.runtime_data.async_set_updated_data(idle)
    with patch(API + "_rpc", AsyncMock()) as rpc, patch(API + "printers", AsyncMock(return_value=idle)), \
            patch(API + "history", AsyncMock(return_value=HISTORY)):
        await hass.services.async_call(DOMAIN, "reprint", {"device_id": dev.id, "file_name": "Benchy.gcode"}, blocking=True)
    assert rpc.call_args.args[1] == {"opGcodeFile": "printprt:/usr/data/printer_data/gcodes/Benchy.gcode"}


async def test_options_flow(hass, printers):
    entry = await _setup(hass, printers)
    hass.services.async_register("notify", "mobile_app_test_phone", AsyncMock())
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["type"] is FlowResultType.FORM
    r = await hass.config_entries.options.async_configure(r["flow_id"], {
        "notify_targets": ["mobile_app_test_phone"], "notify_events": ["finished"], "notify_image": True})
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["notify_targets"] == ["mobile_app_test_phone"]


async def test_notification_sent(hass, printers):
    entry = await _setup(hass, printers)
    calls = []

    async def _phone(call):
        calls.append(call.data)

    hass.services.async_register("notify", "mobile_app_test_phone", _phone)
    hass.config_entries.async_update_entry(entry, options={
        "notify_targets": ["mobile_app_test_phone"], "notify_events": ["finished"], "notify_image": True})
    done = {k: type(v)(**{**v.__dict__, "state": "finished", "thumbnail": None}) for k, v in printers.items()}
    with patch(API + "printers", AsyncMock(return_value=done)), patch(API + "history", AsyncMock(return_value=HISTORY)):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
    assert len(calls) == 1
    assert "finished" in calls[0]["title"] or "klaar" in calls[0]["title"]
    assert calls[0]["data"]["image"].startswith("https://pic2-cdn.creality.com/")



async def test_firmware_list_behind_printer(hass, printers):
    entry = await _setup(hass, printers)
    entry.runtime_data.firmware["TESTDEVICE"] = "1.0.0.1"
    entry.runtime_data.async_update_listeners()
    fw = hass.states.get(_eid(hass, "update", "firmware"))
    assert fw.state == "off" and fw.attributes["latest_version"] == fw.attributes["installed_version"]



async def test_history_right_after_boot(hass, printers):
    """time.monotonic() is small on a freshly booted machine; history and firmware must still load at startup."""
    with patch("custom_components.creality_cloud.coordinator.time.monotonic", return_value=12.0):
        await _setup(hass, printers)
    assert hass.states.get(_eid(hass, "sensor", "last_print")).state == "Benchy.stl_PLA_1h2m3s.gcode"
