"""Config- und Options-Flow für Fridolin Display.

Der Einrichtungsdialog (Config Flow) fragt einmalig nach dem
Standort-Tracker und dem OpenWeatherMap-API-Key. Über den
"Konfigurieren"-Button der Integration (Options Flow) lässt sich danach
jederzeit ändern, welche Licht- und Heizungs-Entities hinter den
Display-Slots stecken - ohne den ESP32 neu zu flashen.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLIMATE_TARGET,
    CONF_DEVICE_TRACKER,
    CONF_LIGHT_SLOT_ENTITY,
    CONF_LIGHT_SLOT_NAME,
    CONF_OWM_API_KEY,
    CONF_OWM_LANG,
    CONF_OWM_UNITS,
    DEFAULT_NAME,
    DEFAULT_OWM_LANG,
    DEFAULT_OWM_UNITS,
    DOMAIN,
    MAX_LIGHT_SLOTS,
)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_TRACKER, default=defaults.get(CONF_DEVICE_TRACKER)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="device_tracker")
            ),
            vol.Required(
                CONF_OWM_API_KEY, default=defaults.get(CONF_OWM_API_KEY, "")
            ): str,
            vol.Optional(
                CONF_OWM_UNITS, default=defaults.get(CONF_OWM_UNITS, DEFAULT_OWM_UNITS)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["metric", "imperial"],
                    translation_key="owm_units",
                )
            ),
            vol.Optional(
                CONF_OWM_LANG, default=defaults.get(CONF_OWM_LANG, DEFAULT_OWM_LANG)
            ): str,
        }
    )


def _entity_mapping_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Baut das Formular für die Licht-/Heizungs-Zuordnung.

    Ein leer gelassener Licht-Slot wird beim Anlegen der Entities
    einfach übersprungen - so kannst du mit 2 Lichtern anfangen und
    später auf bis zu MAX_LIGHT_SLOTS erweitern, ohne Codeänderung.
    """
    defaults = defaults or {}
    schema_dict: dict[Any, Any] = {}

    for index in range(1, MAX_LIGHT_SLOTS + 1):
        entity_key = CONF_LIGHT_SLOT_ENTITY.format(index=index)
        name_key = CONF_LIGHT_SLOT_NAME.format(index=index)
        schema_dict[
            vol.Optional(entity_key, default=defaults.get(entity_key, ""))
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="light"))
        schema_dict[
            vol.Optional(name_key, default=defaults.get(name_key, f"Licht {index}"))
        ] = str

    schema_dict[
        vol.Optional(
            CONF_CLIMATE_TARGET, default=defaults.get(CONF_CLIMATE_TARGET, "")
        )
    ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="climate"))

    return vol.Schema(schema_dict)


class FridolinDisplayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ersteinrichtung: Standort-Tracker + OpenWeatherMap-Zugangsdaten."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Nur eine Instanz dieser Integration ergibt Sinn (ein Display)
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            if not user_input[CONF_OWM_API_KEY].strip():
                errors[CONF_OWM_API_KEY] = "api_key_required"
            else:
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> "FridolinDisplayOptionsFlow":
        return FridolinDisplayOptionsFlow(config_entry)


class FridolinDisplayOptionsFlow(OptionsFlow):
    """Options-Flow: Licht-/Heizungs-Zuordnung, jederzeit änderbar."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            # Leere Strings statt "kein Licht zugewiesen" wieder sauber
            # als leer speichern (EntitySelector liefert bei "nichts
            # gewählt" None zurück, nicht "")
            cleaned = {
                key: (value if value not in (None, "") else "")
                for key, value in user_input.items()
            }
            return self.async_create_entry(title="", data=cleaned)

        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_entity_mapping_schema(current),
        )
