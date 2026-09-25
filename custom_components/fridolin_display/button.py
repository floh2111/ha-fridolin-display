"""Der 'Standort übernehmen'-Button, den das Display auf der
Einstellungsseite aufruft (button.fridolin_standort_uebernehmen).

Liest beim Drücken Breiten-/Längengrad aus dem in den Optionen
gewählten device_tracker aus, übergibt sie dem Wetter-Coordinator und
stößt sofort eine neue Wetterabfrage an.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_LATITUDE, ATTR_LONGITUDE, CONF_DEVICE_TRACKER, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FridolinWeatherCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FridolinWeatherCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FridolinStandortUebernehmenButton(entry, coordinator)])


class FridolinStandortUebernehmenButton(ButtonEntity):
    _attr_name = "Standort übernehmen"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_standort_uebernehmen"
        self.entity_id = "button.fridolin_standort_uebernehmen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Fridolin Display",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_press(self) -> None:
        config = {**self._entry.data, **self._entry.options}
        tracker_entity_id = config.get(CONF_DEVICE_TRACKER)
        if not tracker_entity_id:
            raise HomeAssistantError(
                "Kein Standort-Tracker konfiguriert (Fridolin Display -> Konfigurieren)"
            )

        state = self.hass.states.get(tracker_entity_id)
        if state is None:
            raise HomeAssistantError(f"Tracker {tracker_entity_id} nicht gefunden")

        latitude = state.attributes.get(ATTR_LATITUDE)
        longitude = state.attributes.get(ATTR_LONGITUDE)
        if latitude is None or longitude is None:
            raise HomeAssistantError(
                f"{tracker_entity_id} liefert aktuell keine Koordinaten"
            )

        self._coordinator.set_location(latitude, longitude)
        self._coordinator.last_location_update = (
            f"Übernommen: {datetime.now().strftime('%d.%m. %H:%M')}"
        )
        await self._coordinator.async_request_refresh()
