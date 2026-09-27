"""Klimaanlage(n): feste Display-Entity(s), spiegeln die in den Optionen
gewählte(n) echte(n) climate-Entity(s) (Heizen/Kühlen/Aus, Zieltemperatur,
sowie ein fester Eco/Normal/Max-Modus als Preset).

Wie viele Klimaanlagen-Seiten es gibt (und damit wie viele
FridolinDisplayClimate-Entities angelegt werden), bestimmt der Seitenplan
(siehe page_plan.py) - die erste Instanz behält aus Kompatibilitätsgründen
die historische Entity-ID climate.fridolin_heizung.
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

from .const import DOMAIN, MANUFACTURER, MODEL, climate_entity_id, climate_target_key
from .page_plan import climate_pages

# Feste Preset-Auswahl fürs Display, unabhängig davon, welche presets die
# echte Zielentität sonst noch anbietet (ähnlich wie die festen Licht-Slots).
# Wird 1:1 als preset_mode an die Zielentität durchgereicht - die muss diese
# drei Werte selbst kennen, sonst tut der Knopf nichts.
PRESET_ECO = "eco"
PRESET_NORMAL = "normal"
PRESET_MAX = "max"
DISPLAY_PRESET_MODES = [PRESET_ECO, PRESET_NORMAL, PRESET_MAX]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    entities: list[FridolinDisplayClimate] = []

    for page in climate_pages(config):
        instance = page["instance"]
        target_entity_id = config.get(climate_target_key(instance))
        if not target_entity_id:
            continue  # keine Zielentität zugewiesen - keine Entity anlegen
        entities.append(
            FridolinDisplayClimate(entry, instance, target_entity_id, page["title"])
        )

    async_add_entities(entities)


class FridolinDisplayClimate(ClimateEntity):
    """Spiegelt eine echte climate-Entity unter climate.fridolin_heizung."""

    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
    _attr_preset_modes = DISPLAY_PRESET_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(
        self,
        entry: ConfigEntry,
        instance: str,
        target_entity_id: str,
        display_name: str,
    ) -> None:
        self._target_entity_id = target_entity_id
        self._attr_name = display_name
        self._attr_unique_id = f"{entry.entry_id}_heizung_{instance}"
        self.entity_id = climate_entity_id(instance)
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_preset_mode = None
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
            HVACMode(state.state)
            if state.state in (HVACMode.HEAT, HVACMode.COOL)
            else HVACMode.OFF
        )
        self._attr_target_temperature = state.attributes.get("temperature")
        self._attr_current_temperature = state.attributes.get("current_temperature")
        # Nur übernehmen, wenn die Zielentität einen unserer drei festen
        # Presets meldet - andere presets der Zielentität bleiben unsichtbar
        target_preset = state.attributes.get("preset_mode")
        self._attr_preset_mode = (
            target_preset if target_preset in DISPLAY_PRESET_MODES else None
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": self._target_entity_id, "hvac_mode": hvac_mode},
            blocking=True,
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": self._target_entity_id, "preset_mode": preset_mode},
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
