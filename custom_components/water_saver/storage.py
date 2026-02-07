from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORE_KEY, STORE_VERSION


@dataclass
class PeriodState:
    start_total_l_hour: float | None = None
    start_total_l_day: float | None = None
    start_total_l_week: float | None = None
    start_total_l_month: float | None = None
    start_total_l_year: float | None = None


class WaterSaverStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, STORE_VERSION, STORE_KEY)

    async def async_load(self) -> PeriodState:
        data = await self._store.async_load()
        if not data:
            return PeriodState()
        return PeriodState(**data)

    async def async_save(self, state: PeriodState) -> None:
        await self._store.async_save(
            {
                "start_total_l_hour": state.start_total_l_hour,
                "start_total_l_day": state.start_total_l_day,
                "start_total_l_week": state.start_total_l_week,
                "start_total_l_month": state.start_total_l_month,
                "start_total_l_year": state.start_total_l_year,
            }
        )
