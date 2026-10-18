"""Buttons: pause, resume and cancel the current print."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CrealityConfigEntry
from .entity import CrealityEntity

# command -> states in which the button makes sense
BUTTONS = {"pause": ("printing",), "resume": ("paused",), "cancel": ("printing", "paused")}


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry, add: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    add(CrealityButton(c, pid, key) for pid in c.data for key in BUTTONS)


class CrealityButton(CrealityEntity, ButtonEntity):
    def __init__(self, coordinator, printer_id: str, key: str) -> None:
        super().__init__(coordinator, printer_id, key)
        self.command = key

    @property
    def available(self) -> bool:
        return super().available and self.printer.online and self.printer.state in BUTTONS[self.command]

    async def async_press(self) -> None:
        if not self.available:
            raise HomeAssistantError("%s is not possible right now (printer is %s)" % (self.command, self.printer.state))
        await self.coordinator.command(self.printer_id, self.command)
