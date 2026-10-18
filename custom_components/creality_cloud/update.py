"""Firmware: installed version and the newest version Creality has released for this printer's hardware."""
from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CrealityConfigEntry
from .entity import CrealityEntity


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry, add: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    add(Firmware(c, pid, "firmware") for pid in c.data)


class Firmware(CrealityEntity, UpdateEntity):
    """Only tells that an update exists; install it on the printer's screen or in the Creality app."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_title = "Creality firmware"

    @property
    def installed_version(self) -> str | None:
        return self.printer.firmware

    @property
    def latest_version(self) -> str | None:
        # unknown, or Creality's list is behind the printer: treat as up to date
        latest, installed = self.coordinator.firmware.get(self.printer_id), self.printer.firmware
        if not latest or not installed:
            return latest or installed
        return latest if _key(latest) > _key(installed) else installed

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        return _key(latest_version) > _key(installed_version)


def _key(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in v.replace("-", ".").split("."))
