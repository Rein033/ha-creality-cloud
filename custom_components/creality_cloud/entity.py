"""Base entity: one device per printer."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Printer
from .const import DOMAIN
from .coordinator import CrealityCoordinator


class CrealityEntity(CoordinatorEntity[CrealityCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CrealityCoordinator, printer_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.printer_id = printer_id
        self._attr_unique_id = "%s_%s" % (printer_id, key)
        self._attr_translation_key = key
        p = self.printer
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, printer_id)},
            name=p.name,
            manufacturer="Creality",
            model=p.model,
            sw_version=p.firmware,
            serial_number=p.serial,
        )

    @property
    def printer(self) -> Printer:
        return self.coordinator.data[self.printer_id]

    @property
    def available(self) -> bool:
        return super().available and self.printer_id in self.coordinator.data
