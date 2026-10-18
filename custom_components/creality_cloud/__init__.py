"""Creality Cloud: Creality printers in Home Assistant through crealitycloud.com, for printers on another network."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_when_setup

from .api import CrealityCloud
from .const import CONF_REGION, CONF_TOKEN, DOMAIN
from .coordinator import CrealityCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.IMAGE, Platform.LIGHT, Platform.SENSOR, Platform.UPDATE]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = "/creality_cloud/creality-print-card.js"

type CrealityConfigEntry = ConfigEntry[CrealityCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the Lovelace card (custom:creality-print-card) and load it on every dashboard."""
    if hass.http is not None:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "www" / "creality-print-card.js"), True)])
    version = (await async_get_integration(hass, DOMAIN)).version

    async def _frontend_ready(hass: HomeAssistant, component: str) -> None:
        add_extra_js_url(hass, "%s?v=%s" % (CARD_URL, version))

    # frontend may still be starting; register the card as soon as it is there
    async_when_setup(hass, "frontend", _frontend_ready)

    async def _reprint(call: ServiceCall) -> None:
        """creality_cloud.reprint: start a file from the printer's own storage again."""
        device = dr.async_get(hass).async_get(call.data["device_id"])
        printer_id = next((i[1] for i in (device.identifiers if device else ()) if i[0] == DOMAIN), None)
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            if printer_id in (entry.runtime_data.data or {}):
                await entry.runtime_data.reprint(printer_id, call.data["file_name"])
                return
        raise ServiceValidationError("Not a Creality Cloud printer")

    hass.services.async_register(DOMAIN, "reprint", _reprint, schema=vol.Schema(
        {vol.Required("device_id"): str, vol.Required("file_name"): str}))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry) -> bool:
    cloud = CrealityCloud(async_get_clientsession(hass), entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD],
                          entry.data.get(CONF_TOKEN), entry.data.get(CONF_REGION, "international"))
    coordinator = CrealityCoordinator(hass, entry, cloud)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CrealityConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
