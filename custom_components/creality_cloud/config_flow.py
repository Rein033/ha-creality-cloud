"""Set up with the e-mail address and password of a Creality Cloud account."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CrealityAuthError, CrealityCloud, CrealityError
from .const import CONF_TOKEN, DOMAIN

SCHEMA = vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str})


class CrealityCloudFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _check(self, email: str, password: str) -> tuple[dict | None, dict[str, str]]:
        cloud = CrealityCloud(async_get_clientsession(self.hass), email, password)
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
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()
            token, errors = await self._check(email, user_input[CONF_PASSWORD])
            if not errors:
                return self.async_create_entry(
                    title=email, data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_TOKEN: token})
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token, errors = await self._check(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_TOKEN: token})
        return self.async_show_form(step_id="reauth_confirm", errors=errors,
                                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                                    description_placeholders={"email": entry.data[CONF_EMAIL]})
