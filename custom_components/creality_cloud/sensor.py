"""Sensors: status, progress, times, temperatures, job name, error code."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CrealityConfigEntry
from .api import STATES, Printer, parse_job
from .entity import CrealityEntity


@dataclass(frozen=True, kw_only=True)
class CrealitySensorDescription(SensorEntityDescription):
    value: Callable[[Printer], Any]


def _temp(key: str, value: Callable[[Printer], Any], enabled: bool = True) -> CrealitySensorDescription:
    return CrealitySensorDescription(
        key=key, value=value, device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, suggested_display_precision=0,
        entity_registry_enabled_default=enabled)


SENSORS: tuple[CrealitySensorDescription, ...] = (
    CrealitySensorDescription(key="status", value=lambda p: p.state, device_class=SensorDeviceClass.ENUM,
                              options=[*STATES.values(), "unknown"]),
    CrealitySensorDescription(key="progress", value=lambda p: p.progress, native_unit_of_measurement=PERCENTAGE,
                              state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0),
    CrealitySensorDescription(key="time_remaining", value=lambda p: p.remaining, device_class=SensorDeviceClass.DURATION,
                              native_unit_of_measurement=UnitOfTime.SECONDS, suggested_unit_of_measurement=UnitOfTime.MINUTES, suggested_display_precision=0),
    CrealitySensorDescription(key="print_start", value=lambda p: datetime.fromtimestamp(p.started, timezone.utc) if p.started else None,
                              device_class=SensorDeviceClass.TIMESTAMP),
    CrealitySensorDescription(key="print_end", value=lambda p: datetime.fromtimestamp(time.time() + p.remaining, timezone.utc).replace(second=0, microsecond=0)
                              if p.remaining is not None else None, device_class=SensorDeviceClass.TIMESTAMP),
    CrealitySensorDescription(key="job_name", value=lambda p: p.job),
    _temp("nozzle_temperature", lambda p: p.nozzle),
    _temp("nozzle_target", lambda p: p.nozzle_target),
    _temp("bed_temperature", lambda p: p.bed),
    _temp("bed_target", lambda p: p.bed_target),
    _temp("chamber_temperature", lambda p: p.chamber),
    CrealitySensorDescription(key="error_code", value=lambda p: p.error or 0, entity_category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(hass: HomeAssistant, entry: CrealityConfigEntry, add: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    add(CrealitySensor(c, pid, d) for pid in c.data for d in SENSORS)
    add(LastPrint(c, pid, "last_print") for pid in c.data)


class CrealitySensor(CrealityEntity, SensorEntity):
    entity_description: CrealitySensorDescription

    def __init__(self, coordinator, printer_id: str, description: CrealitySensorDescription) -> None:
        super().__init__(coordinator, printer_id, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value(self.printer)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "job_name":   # same attribute names as the Anycubic integration uses
            return parse_job(self.printer.job) or None
        return None


class LastPrint(CrealityEntity, SensorEntity):
    """The most recent print; the attribute "history" holds the last prints for the card (timelapse, print again)."""

    _attr_icon = "mdi:history"

    @property
    def _records(self):
        return self.coordinator.history.get(self.printer_id) or []

    @property
    def native_value(self) -> str | None:
        r = self._records
        return (r[0].name.rsplit("/", 1)[-1][:250] or None) if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self._records
        return {
            "history": [x.as_dict() for x in r],
            "last_state": r[0].state if r else None,
            "prints_finished": sum(1 for x in r if x.state == "finished"),
        }
