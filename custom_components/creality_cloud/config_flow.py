"""Set up with a Creality Cloud account (region, e-mail or phone, password); options for notifications."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector, SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode,
)

from .api import REGIONS, CrealityAuthError, CrealityCloud, CrealityError
from .const import (
    CONF_NOTIFY_EVENTS, CONF_NOTIFY_IMAGE, CONF_NOTIFY_TARGETS, CONF_REGION, CONF_TOKEN, DEFAULT_NOTIFY_EVENTS, DOMAIN,
    NOTIFY_EVENTS,
)

REGION_SELECTOR = SelectSelector(SelectSelectorConfig(options=list(REGIONS), translation_key="region",
                                                      mode=SelectSelectorMode.DROPDOWN))
SCHEMA = vol.Schema({
    vol.Required(CONF_REGION, default="international"): REGION_SELECTOR,
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
})


class CrealityCloudFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CrealityOptionsFlow()

    async def _check(self, email: str, password: str, region: str) -> tuple[dict | None, dict[str, str]]:
        cloud = CrealityCloud(async_get_clientsession(self.hass), email, password, region=region)
        try:
            token = await cloud.login()
            await cloud.printers()
        except CrealityAuthError:
            return None, {"base": "invalid_auth"}
        except CrealityError:
            return None, {"base": "cannot_connect"}
        return token, {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            region = user_input.get(CONF_REGION, "international")
            await self.async_set_unique_id("%s:%s" % (region, email) if region != "international" else email)
            self._abort_if_unique_id_configured()
            token, errors = await self._check(email, user_input[CONF_PASSWORD], region)
            if not errors:
                return self.async_create_entry(title=email, data={
                    CONF_REGION: region, CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_TOKEN: token},
                    options={CONF_NOTIFY_TARGETS: [], CONF_NOTIFY_EVENTS: DEFAULT_NOTIFY_EVENTS, CONF_NOTIFY_IMAGE: True})
        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input),
                                    errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token, errors = await self._check(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD],
                                              entry.data.get(CONF_REGION, "international"))
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_TOKEN: token})
        return self.async_show_form(step_id="reauth_confirm", errors=errors,
                                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                                    description_placeholders={"email": entry.data[CONF_EMAIL]})


class CrealityOptionsFlow(OptionsFlow):
    """Notifications: to which devices, for which events, with or without the preview image."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        services = sorted(self.hass.services.async_services_for_domain("notify"))
        targets = [SelectOptionDict(value=s, label=self._label(s)) for s in services if s not in ("notify", "persistent_notification")]
        current = self.config_entry.options
        schema = vol.Schema({
            vol.Optional(CONF_NOTIFY_TARGETS, default=[t for t in current.get(CONF_NOTIFY_TARGETS, []) if t in services]):
                SelectSelector(SelectSelectorConfig(options=targets, multiple=True, mode=SelectSelectorMode.DROPDOWN)),
            vol.Optional(CONF_NOTIFY_EVENTS, default=current.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)):
                SelectSelector(SelectSelectorConfig(options=NOTIFY_EVENTS, multiple=True, translation_key="notify_event",
                                                    mode=SelectSelectorMode.LIST)),
            vol.Optional(CONF_NOTIFY_IMAGE, default=current.get(CONF_NOTIFY_IMAGE, True)): BooleanSelector(),
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    def _label(self, service: str) -> str:
        """Show the phone's name for mobile_app_* services."""
        if service.startswith("mobile_app_"):
            from homeassistant.helpers import device_registry as dr
            slug = service.removeprefix("mobile_app_")
            for dev in dr.async_get(self.hass).devices.values():
                name = dev.name_by_user or dev.name or ""
                if name and name.lower().replace(" ", "_").replace("-", "_") == slug:
                    return "%s (%s)" % (name, service)
        return service
