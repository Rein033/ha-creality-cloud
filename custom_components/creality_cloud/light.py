"""The printer's LED light."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CrealityConfigEntry
from .entity import CrealityEntity


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry, add: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    add(CrealityLight(c, pid, "light") for pid, p in c.data.items() if p.light is not None)


class CrealityLight(CrealityEntity, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def available(self) -> bool:
        return super().available and self.printer.online

    @property
    def is_on(self) -> bool | None:
        return self.printer.light

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.command(self.printer_id, "light_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.command(self.printer_id, "light_off")
