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
    add(ReprintLast(c, pid, "reprint_last") for pid in c.data)


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


class ReprintLast(CrealityEntity, ButtonEntity):
    """Start the most recent print again, from the printer's own storage."""

    @property
    def _last(self):
        return next((r for r in self.coordinator.history.get(self.printer_id) or []
                     if r.on_printer and r.state not in ("printing", "paused", "waiting")), None)

    @property
    def available(self) -> bool:
        p = self.printer if self.printer_id in self.coordinator.data else None
        return super().available and p is not None and p.online and not p.active and self._last is not None

    @property
    def extra_state_attributes(self) -> dict | None:
        return {"file_name": self._last.name} if self._last else None

    async def async_press(self) -> None:
        last = self._last
        if not self.available or last is None:
            raise HomeAssistantError("Nothing to print again right now (printer busy, offline or no file on the printer)")
        await self.coordinator.reprint(self.printer_id, last.name)
