"""Config flow, entities and commands inside a real Home Assistant test instance (cloud mocked)."""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.creality_cloud.api import CrealityAuthError
from custom_components.creality_cloud.const import CONF_TOKEN, DOMAIN

API = "custom_components.creality_cloud.api.CrealityCloud."
TOKEN = {"token": "t", "uid": 1}


async def _setup(hass, printers):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="a@b.c", title="a@b.c",
                            data={CONF_EMAIL: "a@b.c", CONF_PASSWORD: "pw", CONF_TOKEN: TOKEN})
    entry.add_to_hass(hass)
    with patch(API + "printers", AsyncMock(return_value=printers)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _eid(hass, platform, key):
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, "TESTDEVICE_" + key)


async def test_config_flow(hass, printers):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert r["type"] is FlowResultType.FORM
    with patch(API + "login", AsyncMock(return_value=TOKEN)), patch(API + "printers", AsyncMock(return_value=printers)):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {CONF_EMAIL: " A@B.c ", CONF_PASSWORD: "pw"})
        await hass.async_block_till_done()
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["title"] == "a@b.c"
    assert r["data"] == {CONF_EMAIL: "a@b.c", CONF_PASSWORD: "pw", CONF_TOKEN: TOKEN}


async def test_config_flow_wrong_password(hass):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(API + "login", AsyncMock(side_effect=CrealityAuthError("nope"))):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {CONF_EMAIL: "a@b.c", CONF_PASSWORD: "x"})
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
    assert "customElements.define('creality-print-card'" in await r.text()


async def test_diagnostics_hide_secrets(hass, printers):
    from custom_components.creality_cloud.diagnostics import async_get_config_entry_diagnostics

    entry = await _setup(hass, printers)
    text = str(await async_get_config_entry_diagnostics(hass, entry))
    for secret in ("a@b.c", "pw", "TESTDEVICE", "TEST-SN", "000000000000", "00000000-test-tbid", "192.0.2.10", "K1Max-TEST"):
        assert secret not in text, secret
    assert "printing" in text
