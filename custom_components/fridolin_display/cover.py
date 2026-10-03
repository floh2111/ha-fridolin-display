"""Rollladen-Slots: feste Display-Entities, die eine echte cover-Entity spiegeln.

Wie bei den Lichtern (siehe light.py) spricht das Display immer feste
Entity-IDs an (cover.fridolin_rollladen_1 ...); welcher echte Rollladen
dahintersteckt, stellst du in den Optionen der Integration ein. Auf/Ab/Stopp
werden an die Ziel-Entity durchgereicht, Zustand und Position live nachgehalten.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    MANUFACTURER,
    MAX_COVER_SLOTS,
    MODEL,
    cover_entity_id,
    cover_slot_entity_key,
    cover_slot_name_key,
)
from .page_plan import cover_pages


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = {**entry.data, **entry.options}
    entities: list[FridolinDisplayCover] = []

    for page in cover_pages(config):
        instance = page["instance"]
        for index in range(1, MAX_COVER_SLOTS + 1):
            target_entity_id = config.get(cover_slot_entity_key(instance, index))
            if not target_entity_id:
                continue  # Slot nicht belegt - keine Entity anlegen
            display_name = config.get(
                cover_slot_name_key(instance, index), f"Rollladen {index}"
            )
            entities.append(
                FridolinDisplayCover(
                    entry, instance, index, target_entity_id, display_name
                )
            )

    async_add_entities(entities)


class FridolinDisplayCover(CoverEntity):
    """Spiegelt eine echte Rollladen-Entity unter einem festen Display-Namen."""

    _attr_should_poll = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(
        self,
        entry: ConfigEntry,
        instance: str,
        slot_index: int,
        target_entity_id: str,
        display_name: str,
    ) -> None:
        self._target_entity_id = target_entity_id
        self._attr_name = display_name
        self._attr_unique_id = f"{entry.entry_id}_rollladen_{instance}_{slot_index}"
        self.entity_id = cover_entity_id(instance, slot_index)
        self._attr_is_closed = None
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._attr_current_cover_position = None
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
        if state is None or state.state in ("unavailable", "unknown"):
            self._attr_available = False
            return
        self._attr_available = True
        self._attr_is_closed = state.state == "closed"
        self._attr_is_opening = state.state == "opening"
        self._attr_is_closing = state.state == "closing"
        self._attr_current_cover_position = state.attributes.get("current_position")

    async def _call(self, service: str) -> None:
        await self.hass.services.async_call(
            "cover", service, {"entity_id": self._target_entity_id}, blocking=True
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._call("open_cover")

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._call("close_cover")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._call("stop_cover")
