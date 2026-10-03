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
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    OWM_CURRENT_URL,
    OWM_FORECAST_URL,
    WEATHER_UPDATE_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "fridolin_display.standort"


def _mm(block: dict[str, Any] | None, key: str) -> float:
    """Niederschlagsmenge (mm) aus einem OWM-Block wie {"1h": 0.4}, sonst 0."""
    try:
        return float((block or {}).get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


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
            weather = entry.get("weather", [{}])[0]
            hours.append(
                {
                    "time": entry.get("dt_txt", "")[11:16],
                    "temperature": round(entry.get("main", {}).get("temp", 0)),
                    "condition": weather.get("description", "—"),
                    "icon": self._map_icon(weather.get("id"), weather.get("icon", "")),
                    "precip": self._precip_text(
                        entry.get("pop"),
                        _mm(entry.get("rain"), "3h") + _mm(entry.get("snow"), "3h"),
                    ),
                }
            )
        # Immer 4 Slots liefern, auch wenn OWM mal weniger zurückgibt
        while len(hours) < 4:
            hours.append(
                {"time": "--:--", "temperature": None, "condition": "—", "icon": "cloudy", "precip": ""}
            )

        tomorrow = self._extract_tomorrow(forecast_list)

        # Ort der Wetterstation laut OpenWeatherMap (z.B. "Freiburg im Breisgau, DE")
        place = current.get("name") or ""
        country = current.get("sys", {}).get("country") or ""
        location = ", ".join(part for part in (place, country) if part) or "—"

        current_weather = current.get("weather", [{}])[0]

        return {
            "location": location,
            "condition": current_weather.get("description", "—"),
            "icon": self._map_icon(current_weather.get("id"), current_weather.get("icon", "")),
            "temperature": current.get("main", {}).get("temp"),
            "wind": self._wind_text(current.get("wind", {}), self._units),
            "humidity": self._humidity_text(current.get("main", {}).get("humidity")),
            "pressure": self._pressure_text(current.get("main", {}).get("pressure")),
            "sunrise": self._local_time(current.get("sys", {}).get("sunrise")),
            "sunset": self._local_time(current.get("sys", {}).get("sunset")),
            "precip": self._precip_now_text(
                _mm(current.get("rain"), "1h") + _mm(current.get("snow"), "1h")
            ),
            "hours": hours,
            "tomorrow": tomorrow,
        }

    @staticmethod
    def _precip_text(pop: float | None, mm: float) -> str:
        """Kompakter Niederschlags-Text fürs Display, z.B. '60% 0,4mm'.

        pop = Regenwahrscheinlichkeit 0..1, mm = Menge im 3h-Slot. Bei
        Trockenheit '0%' (nicht leer), damit man sieht, dass die Anzeige
        arbeitet."""
        percent = round((pop or 0) * 100)
        amount = f"{mm:.1f}".replace(".", ",")
        if mm >= 0.1:
            return f"{percent}% {amount}mm"
        return f"{percent}%"

    @staticmethod
    def _wind_text(wind: dict[str, Any], units: str) -> str:
        """Wind als Text, z.B. '12 km/h NW' (zweite Zeile 'Böen 25 km/h')."""
        speed = wind.get("speed")
        if speed is None:
            return "—"
        if units == "imperial":
            factor, unit = 1.0, "mph"
        else:  # metric/standard liefern m/s
            factor, unit = 3.6, "km/h"
        directions = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
        deg = wind.get("deg")
        direction = f" {directions[round(deg / 45) % 8]}" if deg is not None else ""
        text = f"{round(speed * factor)} {unit}{direction}"
        gust = wind.get("gust")
        if gust is not None and round(gust * factor) > round(speed * factor):
            text += f"\nBöen {round(gust * factor)} {unit}"
        return text

    @staticmethod
    def _humidity_text(humidity: float | None) -> str:
        return "—" if humidity is None else f"{round(humidity)} %"

    @staticmethod
    def _pressure_text(pressure: float | None) -> str:
        return "—" if pressure is None else f"{round(pressure)} hPa"

    @staticmethod
    def _local_time(timestamp: int | None) -> str:
        if not timestamp:
            return "--:--"
        return dt_util.as_local(dt_util.utc_from_timestamp(timestamp)).strftime("%H:%M")

    @staticmethod
    def _precip_now_text(mm: float) -> str:
        if mm < 0.1:
            return "Kein Niederschlag"
        return f"Niederschlag: {f'{mm:.1f}'.replace('.', ',')} mm/h"

    @staticmethod
    def _extract_tomorrow(forecast_list: list[dict[str, Any]]) -> dict[str, Any]:
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        matching = [e for e in forecast_list if e.get("dt_txt", "").startswith(tomorrow_date)]

        if not matching:
            return {"min": None, "max": None, "condition": "—", "icon": "cloudy"}

        temps = [e.get("main", {}).get("temp") for e in matching if e.get("main")]
        mid_entry = matching[len(matching) // 2]
        mid_weather = mid_entry.get("weather", [{}])[0]

        return {
            "min": round(min(temps)) if temps else None,
            "max": round(max(temps)) if temps else None,
            "condition": mid_weather.get("description", "—"),
            "icon": FridolinWeatherCoordinator._map_icon(
                mid_weather.get("id"), mid_weather.get("icon", "")
            ),
        }

    @staticmethod
    def _map_icon(owm_id: int | None, owm_icon: str) -> str:
        """OpenWeatherMap-Zustand auf einen der Icon-Dateinamen im Display abbilden.

        Folgt derselben Gruppierung wie die offizielle OpenWeatherMap-Integration
        von Home Assistant (Wettercode-Bereiche -> "condition"), ergänzt um eine
        eigene Tag-/Nacht-Variante für "partlycloudy" (aus dem 'd'/'n'-Suffix von
        OWM). Nicht jeder Einzelfall ist gegen echte Wetterlagen geprüft - bei
        einem offensichtlich falschen Icon im Display hier nachjustieren.
        """
        night = owm_icon.endswith("n")

        if owm_id is None:
            return "cloudy"
        if owm_id in (200, 201, 202, 230, 231, 232):
            return "lightning-rainy"
        if owm_id in (210, 211, 212, 221):
            return "lightning"
        if 300 <= owm_id <= 321:
            return "rainy"
        if owm_id in (500, 501, 520):
            return "rainy"
        if owm_id in (502, 503, 504, 511, 521, 522, 531):
            return "pouring"
        if owm_id in (611, 612, 613, 615, 616):
            return "snowy-rainy"
        if 600 <= owm_id <= 622:
            return "snowy"
        if owm_id == 771:
            return "windy"
        if owm_id == 781:
            return "exceptional"
        if 701 <= owm_id <= 762:
            return "fog"
        if owm_id == 800:
            return "clear-night" if night else "sunny"
        if owm_id == 801:
            return "partly-cloudy-night" if night else "partlycloudy"
        if 802 <= owm_id <= 804:
            return "cloudy"
        return "cloudy"
