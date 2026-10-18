"""Polls Creality Cloud for all printers on the account."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CrealityAuthError, CrealityCloud, CrealityError, Printer
from .const import CONF_TOKEN, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class CrealityCoordinator(DataUpdateCoordinator[dict[str, Printer]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cloud: CrealityCloud) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL, config_entry=entry)
        self.cloud = cloud

    async def _async_update_data(self) -> dict[str, Printer]:
        old = self.cloud.token
        try:
            data = await self.cloud.printers()
        except CrealityAuthError as ex:
            raise ConfigEntryAuthFailed(str(ex)) from ex
        except CrealityError as ex:
            raise UpdateFailed(str(ex)) from ex
        if self.cloud.token != old:  # keep the new token so a restart does not log in again
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, CONF_TOKEN: self.cloud.token})
        return data

    async def command(self, printer_id: str, name: str) -> None:
        try:
            await self.cloud.command(self.data[printer_id], name)
        except CrealityError as ex:
            raise UpdateFailed(str(ex)) from ex
        await self.async_request_refresh()
