import logging
LOGGER = logging.getLogger(__name__)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_NAME, CONF_TOPIC
from .storage import PeriodState, WaterSaverStore


@dataclass
class WaterData:
    total_l: float | None = None
    target_l: float | None = None
    target_date: str | None = None
    battery_y: float | None = None
    status: str | None = None
    power_mode: str | None = None
    rssi_dbm: float | None = None
    meter_id: str | None = None
    last_payload_ts: str | None = None
    last_rx_utc: datetime | None = None

    hour_l: float | None = None
    day_l: float | None = None
    week_l: float | None = None
    month_l: float | None = None
    year_l: float | None = None

    last_seen_min: int | None = None


class WaterSaverCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME))
        self.topic = entry.options.get(CONF_TOPIC, entry.data.get(CONF_TOPIC))

        self.store = WaterSaverStore(hass)
        self.periods: PeriodState | None = None

        self.data = WaterData()
        self._unsub_mqtt = None
        self._unsub_tick = None

        self._listeners: list[callable] = []

    def add_listener(self, cb: callable) -> None:
        self._listeners.append(cb)

    def _notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    async def async_initialize(self) -> None:
        self.periods = await self.store.async_load()

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

        # Update "last_seen_min" every minute
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

        if self.periods is not None:
            await self.store.async_save(self.periods)

    @callback
    def _tick_last_seen(self, _now: datetime) -> None:
        if self.data.last_rx_utc is None:
            return

        mins = int((dt_util.utcnow() - self.data.last_rx_utc).total_seconds() // 60)
        if self.data.last_seen_min != mins:
            self.data.last_seen_min = mins
            self._notify()

    def _handle_payload(self, payload: str) -> None:
        try:
            import json

            obj: dict[str, Any] = json.loads(payload)
        except Exception:
            return

        # Only care about telegram payloads
        if obj.get("_") != "telegram":
            return

        total_m3 = obj.get("total_m3")
        if total_m3 is None:
            return

        total_l = float(total_m3) * 1000.0
        now_utc = dt_util.utcnow()

        self.data.total_l = total_l
        self.data.target_l = (
            (float(obj["target_m3"]) * 1000.0)
            if obj.get("target_m3") is not None
            else None
        )
        self.data.target_date = obj.get("target_date")
        self.data.battery_y = (
            float(obj["battery_y"]) if obj.get("battery_y") is not None else None
        )
        self.data.status = obj.get("status")
        self.data.power_mode = obj.get("power_mode")
        self.data.rssi_dbm = (
            float(obj["rssi_dbm"]) if obj.get("rssi_dbm") is not None else None
        )
        self.data.meter_id = str(obj.get("id")) if obj.get("id") is not None else None
        self.data.last_payload_ts = obj.get("timestamp")
        self.data.last_rx_utc = now_utc
        self.data.last_seen_min = 0

        # Compute period deltas
        self._update_period_deltas(total_l, now_utc)

        self._notify()

    def _update_period_deltas(self, total_l: float, now_utc: datetime) -> None:
        assert self.periods is not None

        local = dt_util.as_local(now_utc)

        # Hour boundary
        if self.periods.start_total_l_hour is None:
            self.periods.start_total_l_hour = total_l
        if local.minute == 0 and local.second < 10:
            self.periods.start_total_l_hour = total_l

        # Day boundary
        if self.periods.start_total_l_day is None:
            self.periods.start_total_l_day = total_l
        if local.hour == 0 and local.minute == 0 and local.second < 10:
            self.periods.start_total_l_day = total_l

        # Week boundary (Monday)
        if self.periods.start_total_l_week is None:
            self.periods.start_total_l_week = total_l
        if (
            local.weekday() == 0
            and local.hour == 0
            and local.minute == 0
            and local.second < 10
        ):
            self.periods.start_total_l_week = total_l

        # Month boundary
        if self.periods.start_total_l_month is None:
            self.periods.start_total_l_month = total_l
        if local.day == 1 and local.hour == 0 and local.minute == 0 and local.second < 10:
            self.periods.start_total_l_month = total_l

        # Year boundary
        if self.periods.start_total_l_year is None:
            self.periods.start_total_l_year = total_l
        if (
            local.month == 1
            and local.day == 1
            and local.hour == 0
            and local.minute == 0
            and local.second < 10
        ):
            self.periods.start_total_l_year = total_l

        # Deltas
        self.data.hour_l = max(
            0.0, total_l - (self.periods.start_total_l_hour or total_l)
        )
        self.data.day_l = max(
            0.0, total_l - (self.periods.start_total_l_day or total_l)
        )
        self.data.week_l = max(
            0.0, total_l - (self.periods.start_total_l_week or total_l)
        )
        self.data.month_l = max(
            0.0, total_l - (self.periods.start_total_l_month or total_l)
        )
        self.data.year_l = max(
            0.0, total_l - (self.periods.start_total_l_year or total_l)
        )
