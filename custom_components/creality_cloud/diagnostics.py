"""Diagnostics for bug reports: everything Creality Cloud returned, with credentials and identifiers removed."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import CrealityConfigEntry
from .const import CONF_TOKEN

REDACT = {
    CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN, "token", "uid", "userId", "ownerUserId", "id", "tb_id", "tbId", "deviceId",
    "deviceName", "deviceSecret", "keyFileToken", "macAddress", "wifiSsid", "factorySn", "productionSn", "serial",
    "netIP", "hostname", "oldId", "printId", "aliasName", "name", "value",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: CrealityConfigEntry) -> dict[str, Any]:
    printers = []
    for p in entry.runtime_data.data.values():
        d = asdict(p)
        raw = d.pop("raw")
        # iotAttr is a list of {key, value}; keep harmless keys readable
        attrs = {a.get("key"): a.get("value") for a in raw.get("iotAttr") or []}
        raw = {k: v for k, v in raw.items() if k != "iotAttr"}
        printers.append({"printer": async_redact_data(d, REDACT - {"value"}),
                         "raw": async_redact_data(raw, REDACT - {"value"}),
                         "attributes": async_redact_data(attrs, REDACT - {"value", "name"})})
    return {"entry": async_redact_data(dict(entry.data), REDACT), "printers": printers}
