from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_SNOOZE_DEFAULT_HOURS,
    DEFAULT_SNOOZE_DEFAULT_HOURS,
    DOMAIN,
    HEROLD_DOMAIN,
    HEROLD_TOPICS,
)
from .coordinator import WaterSaverCoordinator

PLATFORMS: list[str] = ["sensor", "binary_sensor", "switch"]

SERVICE_SNOOZE = "snooze"
SERVICE_UNSNOOZE = "unsnooze"

SNOOZE_SCHEMA = vol.Schema({
    vol.Optional("hours"): vol.Coerce(float),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = WaterSaverCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Topic subscription and exclusion-entity tracking are wired up once in
    # coordinator.async_initialize(); reload so option changes take effect.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Register services (once per domain)
    if not hass.services.has_service(DOMAIN, SERVICE_SNOOZE):
        async def handle_snooze(call: ServiceCall) -> None:
            hours = call.data.get(
                "hours",
                entry.options.get(CONF_SNOOZE_DEFAULT_HOURS, DEFAULT_SNOOZE_DEFAULT_HOURS),
            )
            for coord in hass.data[DOMAIN].values():
                coord.set_snooze(hours)

        async def handle_unsnooze(call: ServiceCall) -> None:
            for coord in hass.data[DOMAIN].values():
                coord.clear_snooze()

        hass.services.async_register(DOMAIN, SERVICE_SNOOZE, handle_snooze, schema=SNOOZE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_UNSNOOZE, handle_unsnooze)

    if HEROLD_DOMAIN in hass.data:
        for topic_id, meta in HEROLD_TOPICS.items():
            await hass.services.async_call(
                HEROLD_DOMAIN,
                "topic_registrieren",
                {"topic": topic_id, "quelle": f"custom_components.{DOMAIN}", **meta},
                blocking=False,
            )

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: WaterSaverCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()

    # Unregister services if no more entries
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SNOOZE)
        hass.services.async_remove(DOMAIN, SERVICE_UNSNOOZE)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
