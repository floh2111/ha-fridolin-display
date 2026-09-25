"""Licht-Slots: feste Display-Entities, die eine echte Licht-Entity spiegeln.

Jede FridolinDisplayLight hält Zustand und Helligkeit ihrer Ziel-Entity
live nach (über einen State-Change-Listener) und reicht toggle/turn_on/
turn_off einfach weiter. Das ESP32-Display spricht immer
light.fridolin_licht_1 / _2 / ... an; welches echte Licht dahinter
hängt, stellst du über die Options-Seite der Integration ein.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_LIGHT_SLOT_ENTITY,
    CONF_LIGHT_SLOT_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    MAX_LIGHT_SLOTS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    entities: list[FridolinDisplayLight] = []

    for index in range(1, MAX_LIGHT_SLOTS + 1):
        target_entity_id = config.get(CONF_LIGHT_SLOT_ENTITY.format(index=index))
        if not target_entity_id:
            continue  # Slot nicht belegt - keine Entity anlegen
        display_name = config.get(
            CONF_LIGHT_SLOT_NAME.format(index=index), f"Licht {index}"
        )
        entities.append(
            FridolinDisplayLight(entry, index, target_entity_id, display_name)
        )

    async_add_entities(entities)


class FridolinDisplayLight(LightEntity):
    """Spiegelt eine echte Licht-Entity unter einem festen Display-Namen."""

    _attr_should_poll = False
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(
        self,
        entry: ConfigEntry,
        slot_index: int,
        target_entity_id: str,
        display_name: str,
    ) -> None:
        self._target_entity_id = target_entity_id
        self._attr_name = display_name
        self._attr_unique_id = f"{entry.entry_id}_licht_{slot_index}"
        # Feste, vorhersagbare Entity-ID fürs ESPHome-Display
        self.entity_id = f"light.fridolin_licht_{slot_index}"
        self._attr_is_on = False
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
        self._attr_is_on = state.state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "light", "turn_on", {"entity_id": self._target_entity_id}, blocking=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "light", "turn_off", {"entity_id": self._target_entity_id}, blocking=True
        )
