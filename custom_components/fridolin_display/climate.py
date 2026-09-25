"""Heizung: feste Display-Entity climate.fridolin_heizung, spiegelt die
in den Optionen gewählte echte climate-Entity (HVAC-Modus + Zieltemperatur).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_CLIMATE_TARGET, DOMAIN, MANUFACTURER, MODEL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    target_entity_id = config.get(CONF_CLIMATE_TARGET)
    if not target_entity_id:
        return  # keine Heizung zugewiesen - keine Entity anlegen

    async_add_entities([FridolinDisplayClimate(entry, target_entity_id)])


class FridolinDisplayClimate(ClimateEntity):
    """Spiegelt eine echte climate-Entity unter climate.fridolin_heizung."""

    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, entry: ConfigEntry, target_entity_id: str) -> None:
        self._target_entity_id = target_entity_id
        self._attr_name = "Heizung"
        self._attr_unique_id = f"{entry.entry_id}_heizung"
        self.entity_id = "climate.fridolin_heizung"
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = None
        self._attr_current_temperature = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Fridolin Display",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self) -> None:
        self._sync_from_target(self.hass.states.get(self._target_entity_id))
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._target_entity_id], self._handle_target_change
            )
        )

    @callback
    def _handle_target_change(self, event: Event) -> None:
        self._sync_from_target(event.data.get("new_state"))
        self.async_write_ha_state()

    @callback
    def _sync_from_target(self, state: State | None) -> None:
        if state is None:
            self._attr_available = False
            return
        self._attr_available = True
        # Der Zustand (state) einer climate-Entity IST der HVAC-Modus
        self._attr_hvac_mode = (
            HVACMode.HEAT if state.state == "heat" else HVACMode.OFF
        )
        self._attr_target_temperature = state.attributes.get("temperature")
        self._attr_current_temperature = state.attributes.get("current_temperature")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": self._target_entity_id, "hvac_mode": hvac_mode},
            blocking=True,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": self._target_entity_id, ATTR_TEMPERATURE: temperature},
            blocking=True,
        )
