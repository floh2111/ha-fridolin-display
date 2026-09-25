"""Wetter-Sensoren fürs Display: aktueller Zustand/Temperatur, vier
Stunden-Slots und der Ausblick auf morgen - alle gespeist vom
FridolinWeatherCoordinator (siehe coordinator.py).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import FridolinWeatherCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FridolinWeatherCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        FridolinWetterZustandSensor(entry, coordinator),
        FridolinWetterTemperaturSensor(entry, coordinator),
        FridolinWetterOrtSensor(entry, coordinator),
        FridolinMorgenMinSensor(entry, coordinator),
        FridolinMorgenMaxSensor(entry, coordinator),
        FridolinMorgenZustandSensor(entry, coordinator),
        FridolinStandortStatusSensor(entry, coordinator),
    ]
    for slot in range(4):
        entities.append(FridolinStundeZeitSensor(entry, coordinator, slot))
        entities.append(FridolinStundeTempSensor(entry, coordinator, slot))
        entities.append(FridolinStundeZustandSensor(entry, coordinator, slot))

    async_add_entities(entities)


class _FridolinBaseSensor(CoordinatorEntity[FridolinWeatherCoordinator], SensorEntity):
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Fridolin Display",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )


class FridolinWetterZustandSensor(_FridolinBaseSensor):
    _attr_name = "Fridolin Wetter Zustand"

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wetter_zustand"
        self.entity_id = "sensor.fridolin_wetter_zustand"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("condition") if self.coordinator.data else None


class FridolinWetterTemperaturSensor(_FridolinBaseSensor):
    _attr_name = "Fridolin Wetter Temperatur"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wetter_temperatur"
        self.entity_id = "sensor.fridolin_wetter_temperatur"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("temperature") if self.coordinator.data else None


class FridolinWetterOrtSensor(_FridolinBaseSensor):
    """Ort, für den OpenWeatherMap gerade das Wetter liefert."""

    _attr_name = "Fridolin Wetter Ort"

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_wetter_ort"
        self.entity_id = "sensor.fridolin_wetter_ort"

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.get("location") if self.coordinator.data else None


class FridolinMorgenMinSensor(_FridolinBaseSensor):
    _attr_name = "Fridolin Wetter Morgen Min"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_morgen_min"
        self.entity_id = "sensor.fridolin_wetter_morgen_min"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("tomorrow", {}).get("min")


class FridolinMorgenMaxSensor(_FridolinBaseSensor):
    _attr_name = "Fridolin Wetter Morgen Max"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_morgen_max"
        self.entity_id = "sensor.fridolin_wetter_morgen_max"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("tomorrow", {}).get("max")


class FridolinMorgenZustandSensor(_FridolinBaseSensor):
    _attr_name = "Fridolin Wetter Morgen Zustand"

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_morgen_zustand"
        self.entity_id = "sensor.fridolin_wetter_morgen_zustand"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("tomorrow", {}).get("condition")


class FridolinStandortStatusSensor(_FridolinBaseSensor):
    """Zeigt an, wann zuletzt 'Standort übernehmen' gedrückt wurde."""

    _attr_name = "Fridolin Standort Status"

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_standort_status"
        self.entity_id = "sensor.fridolin_standort_status"

    @property
    def native_value(self) -> Any:
        return self.coordinator.last_location_update or "Noch kein Standort übernommen"


class FridolinStundeZeitSensor(_FridolinBaseSensor):
    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator, slot: int) -> None:
        super().__init__(entry, coordinator)
        self._slot = slot
        self._attr_name = f"Fridolin Wetter Stunde {slot} Zeit"
        self._attr_unique_id = f"{entry.entry_id}_h{slot}_zeit"
        self.entity_id = f"sensor.fridolin_wetter_h{slot}_zeit"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("hours", [])[self._slot].get("time")


class FridolinStundeTempSensor(_FridolinBaseSensor):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator, slot: int) -> None:
        super().__init__(entry, coordinator)
        self._slot = slot
        self._attr_name = f"Fridolin Wetter Stunde {slot} Temperatur"
        self._attr_unique_id = f"{entry.entry_id}_h{slot}_temp"
        self.entity_id = f"sensor.fridolin_wetter_h{slot}_temp"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("hours", [])[self._slot].get("temperature")


class FridolinStundeZustandSensor(_FridolinBaseSensor):
    def __init__(self, entry: ConfigEntry, coordinator: FridolinWeatherCoordinator, slot: int) -> None:
        super().__init__(entry, coordinator)
        self._slot = slot
        self._attr_name = f"Fridolin Wetter Stunde {slot} Zustand"
        self._attr_unique_id = f"{entry.entry_id}_h{slot}_zustand"
        self.entity_id = f"sensor.fridolin_wetter_h{slot}_zustand"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("hours", [])[self._slot].get("condition")
