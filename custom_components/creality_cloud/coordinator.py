"""Polls Creality Cloud for all printers on the account, plus history and firmware, and sends notifications."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CrealityAuthError, CrealityCloud, CrealityError, Printer, PrintRecord
from .const import (
    CONF_NOTIFY_EVENTS, CONF_NOTIFY_IMAGE, CONF_NOTIFY_TARGETS, CONF_TOKEN, DOMAIN, FIRMWARE_INTERVAL, HISTORY_INTERVAL,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

MESSAGES = {
    "en": {"finished": "{name}: print finished", "failed": "{name}: print failed", "stopped": "{name}: print cancelled",
           "paused": "{name}: print paused", "offline": "{name} is offline", "error": "{name}: error {code}",
           "started": "{name}: print started"},
    "nl": {"finished": "{name}: print klaar", "failed": "{name}: print mislukt", "stopped": "{name}: print geannuleerd",
           "paused": "{name}: print gepauzeerd", "offline": "{name} is offline", "error": "{name}: fout {code}",
           "started": "{name}: print gestart"},
}


def events_between(old: Printer | None, new: Printer) -> list[str]:
    """Which notification events a state change means (no network; tested)."""
    if old is None:
        return []
    out = []
    if old.online and not new.online:
        out.append("offline")
    if new.online and new.state != old.state:
        if new.state in ("finished", "failed", "stopped", "paused"):
            out.append(new.state)
        elif new.state == "printing" and old.state not in ("printing", "paused"):
            out.append("started")
    if new.error and new.error != old.error:
        out.append("error")
    return out


class CrealityCoordinator(DataUpdateCoordinator[dict[str, Printer]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cloud: CrealityCloud) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL, config_entry=entry)
        self.cloud = cloud
        self.history: dict[str, list[PrintRecord]] = {}
        self.firmware: dict[str, str | None] = {}
        self._history_at = 0.0
        self._firmware_at = 0.0
        self._last_thumb: dict[str, str] = {}

    async def _async_update_data(self) -> dict[str, Printer]:
        old_token, old = self.cloud.token, self.data
        try:
            data = await self.cloud.printers()
        except CrealityAuthError as ex:
            raise ConfigEntryAuthFailed(str(ex)) from ex
        except CrealityError as ex:
            raise UpdateFailed(str(ex)) from ex
        if self.cloud.token != old_token:  # keep the new token so a restart does not log in again
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, CONF_TOKEN: self.cloud.token})

        changed = old is not None and any(old.get(k) and old[k].state != p.state for k, p in data.items())
        now = time.monotonic()
        if changed or now - self._history_at > HISTORY_INTERVAL.total_seconds():
            self._history_at = now
            await self._refresh_history(data)
        if now - self._firmware_at > FIRMWARE_INTERVAL.total_seconds():
            self._firmware_at = now
            await self._refresh_firmware(data)

        if old is not None:
            for pid, p in data.items():
                for event in events_between(old.get(pid), p):
                    await self._notify(p, event)
        for pid, p in data.items():
            if p.thumbnail:
                self._last_thumb[pid] = p.thumbnail
        return data

    async def _refresh_history(self, data: dict[str, Printer]) -> None:
        for pid, p in data.items():
            try:
                self.history[pid] = await self.cloud.history(p)
            except CrealityError as ex:
                _LOGGER.debug("history for %s failed: %s", p.name, ex)

    async def _refresh_firmware(self, data: dict[str, Printer]) -> None:
        for pid, p in data.items():
            try:
                self.firmware[pid] = await self.cloud.latest_firmware(p.hardware)
            except CrealityError as ex:
                _LOGGER.debug("firmware check for %s failed: %s", p.name, ex)

    async def _notify(self, p: Printer, event: str) -> None:
        opts: dict[str, Any] = self.config_entry.options
        targets = opts.get(CONF_NOTIFY_TARGETS) or []
        if not targets or event not in (opts.get(CONF_NOTIFY_EVENTS) or []):
            return
        lang = "nl" if (self.hass.config.language or "").startswith("nl") else "en"
        title = MESSAGES[lang][event].format(name=p.name, code=p.error)
        hist = self.history.get(p.id) or []
        job = p.job or (hist[0].name if hist else "")
        message = (job or "").rsplit("/", 1)[-1] or p.model
        data: dict[str, Any] = {"tag": "creality_cloud_%s" % p.id, "group": "creality_cloud"}
        image = p.thumbnail or self._last_thumb.get(p.id)
        if opts.get(CONF_NOTIFY_IMAGE, True) and image:
            data["image"] = image
        for target in targets:
            service = target.removeprefix("notify.")
            if not self.hass.services.has_service("notify", service):
                _LOGGER.warning("notify.%s does not exist (anymore); check the Creality Cloud options", service)
                continue
            try:
                await self.hass.services.async_call("notify", service, {"title": title, "message": message, "data": data})
            except HomeAssistantError as ex:
                _LOGGER.warning("notify.%s failed: %s", service, ex)

    async def command(self, printer_id: str, name: str) -> None:
        try:
            await self.cloud.command(self.data[printer_id], name)
        except CrealityError as ex:
            raise HomeAssistantError(str(ex)) from ex
        await self.async_request_refresh()

    async def reprint(self, printer_id: str, file_name: str) -> None:
        try:
            await self.cloud.reprint(self.data[printer_id], file_name)
        except (CrealityError, ValueError) as ex:
            raise HomeAssistantError(str(ex)) from ex
        await self.async_request_refresh()
