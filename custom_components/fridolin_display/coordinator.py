"""DataUpdateCoordinator für das Wetter am jeweils übernommenen Standort.

Ersetzt die frühere REST-Sensor-/Jinja-Template-Lösung: holt aktuelles
Wetter + 5-Tage/3-Stunden-Vorhersage von OpenWeatherMap für die
Koordinaten, die zuletzt per "Standort übernehmen" gespeichert wurden
(Fallback: Home-Assistant-Heimatstandort, bis das erste Mal übernommen
wurde).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    OWM_CURRENT_URL,
    OWM_FORECAST_URL,
    WEATHER_UPDATE_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "fridolin_display.standort"


class FridolinWeatherCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holt aktuelles Wetter + Vorhersage und bereitet sie fürs Display auf."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        units: str,
        lang: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Fridolin Wetter",
            update_interval=timedelta(minutes=WEATHER_UPDATE_INTERVAL_MINUTES),
        )
        self._api_key = api_key
        self._units = units
        self._lang = lang
        # Fällt auf den Home-Assistant-Heimatstandort zurück, bis
        # "Standort übernehmen" das erste Mal gedrückt wurde
        self.latitude: float = hass.config.latitude
        self.longitude: float = hass.config.longitude
        self.last_location_update: str | None = None
        # Übernommener Standort überlebt Neustarts von Home Assistant
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load_location(self) -> None:
        """Gespeicherten Standort laden (vor dem ersten Wetterabruf aufrufen)."""
        saved = await self._store.async_load()
        if not saved:
            return
        try:
            self.latitude = float(saved["latitude"])
            self.longitude = float(saved["longitude"])
        except (KeyError, TypeError, ValueError):
            return
        self.last_location_update = saved.get("last_update")

    async def async_set_location(
        self, latitude: float, longitude: float, last_update: str
    ) -> None:
        """Wird vom Button 'Standort übernehmen' aufgerufen und speichert dauerhaft."""
        self.latitude = latitude
        self.longitude = longitude
        self.last_location_update = last_update
        await self._store.async_save(
            {"latitude": latitude, "longitude": longitude, "last_update": last_update}
        )

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        params = {
            "lat": self.latitude,
            "lon": self.longitude,
            "appid": self._api_key,
            "units": self._units,
            "lang": self._lang,
        }

        try:
            async with async_timeout.timeout(15):
                current_resp = await session.get(OWM_CURRENT_URL, params=params)
                current_resp.raise_for_status()
                current = await current_resp.json()

            async with async_timeout.timeout(15):
                forecast_resp = await session.get(OWM_FORECAST_URL, params=params)
                forecast_resp.raise_for_status()
                forecast = await forecast_resp.json()
        except Exception as err:  # noqa: BLE001 - alles wird als UpdateFailed gemeldet
            raise UpdateFailed(f"Fehler beim Abruf von OpenWeatherMap: {err}") from err

        return self._parse(current, forecast)

    def _parse(self, current: dict[str, Any], forecast: dict[str, Any]) -> dict[str, Any]:
        forecast_list: list[dict[str, Any]] = forecast.get("list", [])

        hours: list[dict[str, Any]] = []
        for entry in forecast_list[:4]:
            hours.append(
                {
                    "time": entry.get("dt_txt", "")[11:16],
                    "temperature": round(entry.get("main", {}).get("temp", 0)),
                    "condition": entry.get("weather", [{}])[0].get("description", "—"),
                }
            )
        # Immer 4 Slots liefern, auch wenn OWM mal weniger zurückgibt
        while len(hours) < 4:
            hours.append({"time": "--:--", "temperature": None, "condition": "—"})

        tomorrow = self._extract_tomorrow(forecast_list)

        # Ort der Wetterstation laut OpenWeatherMap (z.B. "Freiburg im Breisgau, DE")
        place = current.get("name") or ""
        country = current.get("sys", {}).get("country") or ""
        location = ", ".join(part for part in (place, country) if part) or "—"

        return {
            "location": location,
            "condition": current.get("weather", [{}])[0].get("description", "—"),
            "temperature": current.get("main", {}).get("temp"),
            "hours": hours,
            "tomorrow": tomorrow,
        }

    @staticmethod
    def _extract_tomorrow(forecast_list: list[dict[str, Any]]) -> dict[str, Any]:
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        matching = [e for e in forecast_list if e.get("dt_txt", "").startswith(tomorrow_date)]

        if not matching:
            return {"min": None, "max": None, "condition": "—"}

        temps = [e.get("main", {}).get("temp") for e in matching if e.get("main")]
        mid_entry = matching[len(matching) // 2]

        return {
            "min": round(min(temps)) if temps else None,
            "max": round(max(temps)) if temps else None,
            "condition": mid_entry.get("weather", [{}])[0].get("description", "—"),
        }
