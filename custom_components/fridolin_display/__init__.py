"""Fridolin Display: konfigurierbare Gegenstelle für das Wohnwagen-Touch-Display.

Legt feste "Display-Entities" an (light.fridolin_licht_*,
climate.fridolin_heizung, sensor.fridolin_wetter_*, button zum
Standort-Übernehmen), die ESPHome fest verdrahtet anspricht. Welche
echten Entities dahinterstecken, wählst du über die Options-Seite
dieser Integration - Änderungen wirken sich sofort aufs Display aus,
ganz ohne Reflash.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_OWM_API_KEY,
    CONF_OWM_LANG,
    CONF_OWM_UNITS,
    DEFAULT_OWM_LANG,
    DEFAULT_OWM_UNITS,
    DOMAIN,
)
from .coordinator import FridolinWeatherCoordinator

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration einrichten."""
    api_key = entry.data[CONF_OWM_API_KEY]
    units = entry.options.get(
        CONF_OWM_UNITS, entry.data.get(CONF_OWM_UNITS, DEFAULT_OWM_UNITS)
    )
    lang = entry.options.get(
        CONF_OWM_LANG, entry.data.get(CONF_OWM_LANG, DEFAULT_OWM_LANG)
    )

    coordinator = FridolinWeatherCoordinator(hass, api_key, units, lang)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bei geänderten Options (z.B. neue Licht-Zuordnung) alles neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
