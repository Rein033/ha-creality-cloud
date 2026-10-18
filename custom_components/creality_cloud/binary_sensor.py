"""Binary sensors: is the printer connected to Creality Cloud, is it printing."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CrealityConfigEntry
from .entity import CrealityEntity


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry, add: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    add(e for pid in c.data for e in (Online(c, pid, "online"), Printing(c, pid, "printing")))


class Online(CrealityEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        return self.printer.online


class Printing(CrealityEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return self.printer.state == "printing"
