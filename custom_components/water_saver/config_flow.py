from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_NAME, CONF_TOPIC, DEFAULT_NAME, DEFAULT_TOPIC, DOMAIN


class WaterSaverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_TOPIC, default=DEFAULT_TOPIC): str,
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        await self.async_set_unique_id(f"{DOMAIN}:{user_input[CONF_TOPIC]}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WaterSaverOptionsFlow(config_entry)


class WaterSaverOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self._entry.data.get(CONF_NAME, DEFAULT_NAME)): str,
                    vol.Required(CONF_TOPIC, default=self._entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)): str,
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        return self.async_create_entry(title="", data=user_input)
