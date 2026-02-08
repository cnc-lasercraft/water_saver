from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_NAME, CONF_TOPIC, DOMAIN

LOGGER = logging.getLogger(__name__)


@dataclass
class WaterSaverData:
    total_m3: float | None = None
    battery_y: float | None = None
    rssi_dbm: float | None = None
    status: str | None = None
    power_mode: str | None = None
    meter_id: str | None = None
    telegram_timestamp: str | None = None
    last_rx_utc: datetime | None = None
    last_seen_min: int | None = None


class WaterSaverCoordinator(DataUpdateCoordinator[WaterSaverData]):
    """Push-based coordinator fed by MQTT (no polling)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self.name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME))
        self.topic = entry.options.get(CONF_TOPIC, entry.data.get(CONF_TOPIC))

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}:{self.name}",
            update_interval=None,
        )

        self._unsub_mqtt = None
        self._unsub_tick = None

        self.async_set_updated_data(WaterSaverData())

    async def async_initialize(self) -> None:
        LOGGER.debug("Water Saver subscribing to MQTT topic=%r", self.topic)

        @callback
        def _msg_received(msg: mqtt.ReceiveMessage) -> None:
            self._handle_payload(msg.payload)

        self._unsub_mqtt = await mqtt.async_subscribe(
            self.hass,
            self.topic,
            _msg_received,
            qos=0,
            encoding="utf-8",
        )

        self._unsub_tick = async_track_time_interval(
            self.hass,
            self._tick_last_seen,
            timedelta(minutes=1),
        )

    async def async_shutdown(self) -> None:
        if self._unsub_mqtt:
            self._unsub_mqtt()
            self._unsub_mqtt = None

        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None

    @callback
    def _tick_last_seen(self, _now: datetime) -> None:
        d = self.data
        if d.last_rx_utc is None:
            return

        mins = int((dt_util.utcnow() - d.last_rx_utc).total_seconds() // 60)
        if d.last_seen_min != mins:
            self.async_set_updated_data(replace(d, last_seen_min=mins))

    def _handle_payload(self, payload: str) -> None:
        try:
            obj: dict[str, Any] = json.loads(payload)
        except Exception:
            return

        if obj.get("_") != "telegram":
            return

        total_m3 = obj.get("total_m3")
        if total_m3 is None:
            return

        now_utc = dt_util.utcnow()

        new_data = WaterSaverData(
            total_m3=float(total_m3),
            battery_y=float(obj["battery_y"]) if obj.get("battery_y") is not None else None,
            rssi_dbm=float(obj["rssi_dbm"]) if obj.get("rssi_dbm") is not None else None,
            status=obj.get("status"),
            power_mode=obj.get("power_mode"),
            meter_id=str(obj.get("id")) if obj.get("id") is not None else None,
            telegram_timestamp=obj.get("timestamp"),
            last_rx_utc=now_utc,
            last_seen_min=0,
        )

        self.async_set_updated_data(new_data)
