"""Preview image of the current print (from Creality's CDN)."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import CrealityConfigEntry
from .entity import CrealityEntity


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry, add: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    add(Thumbnail(hass, c, pid) for pid in c.data)


class Thumbnail(CrealityEntity, ImageEntity):
    def __init__(self, hass: HomeAssistant, coordinator, printer_id: str) -> None:
        CrealityEntity.__init__(self, coordinator, printer_id, "thumbnail")
        ImageEntity.__init__(self, hass)
        self._url = self.printer.thumbnail
        self._attr_image_last_updated = dt_util.utcnow()

    @property
    def image_url(self) -> str | None:
        return self.printer.thumbnail

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.printer_id in self.coordinator.data and self.printer.thumbnail != self._url:
            self._url = self.printer.thumbnail
            self._cached_image = None
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    @property
    def image_last_updated(self) -> datetime | None:
        return self._attr_image_last_updated
