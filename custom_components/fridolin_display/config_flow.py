"""Config- und Options-Flow für Fridolin Display.

Der Einrichtungsdialog (Config Flow) fragt einmalig nach dem
Standort-Tracker und dem OpenWeatherMap-API-Key. Über den
"Konfigurieren"-Button der Integration (Options Flow) lässt sich danach
jederzeit ändern:
  1. der Seitenplan (welche Seiten das Display in welcher Reihenfolge
     zeigt, siehe page_plan.py) - als JSON-Liste editierbar. Eine
     Änderung der Seiten-*Auswahl/Reihenfolge* braucht ein neu
     generiertes + geflashtes Display (siehe esphome/generate_display_yaml.py),
     eine Änderung *innerhalb* eines bestehenden Licht-/Klimaanlagen-Slots
     (welche echte Entity dahintersteckt) dagegen nicht.
  2. welche echten Licht-/Heizungs-Entities hinter den Slots aus dem
     Seitenplan stecken - wirkt sofort, ohne den ESP32 neu zu flashen.
"""

from __future__ import annotations

import json
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_TRACKER,
    CONF_OWM_API_KEY,
    CONF_OWM_LANG,
    CONF_OWM_UNITS,
    CONF_PAGE_PLAN,
    DEFAULT_NAME,
    DEFAULT_OWM_LANG,
    DEFAULT_OWM_UNITS,
    DOMAIN,
    MAX_LIGHT_SLOTS,
    PAGE_TYPES,
    light_slot_entity_key,
    light_slot_name_key,
    climate_target_key,
)
from .page_plan import get_page_plan


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


def _page_plan_schema(current_plan: list[dict[str, Any]]) -> vol.Schema:
    """Seitenplan als JSON-Liste editierbar (siehe page_plan.py).

    Bewusst ein einzelnes JSON-Textfeld statt einer Formular-Frage pro
    Seite: eine "wiederholbare Gruppe von Feldern" (Seite hinzufügen/
    entfernen/verschieben) gibt es in Home Assistants Selector-System
    nicht eingebaut - ein Multi-Step-Wizard dafür ist ein separates,
    größeres Stück Arbeit. Das JSON-Feld ist der pragmatische erste
    Schritt, den technisch versierte Nutzer direkt nutzen können.
    """
    return vol.Schema(
        {
            vol.Required(
                "page_plan_json",
                default=json.dumps(current_plan, ensure_ascii=False, indent=2),
            ): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
        }
    )


def _entity_mapping_schema(
    plan: list[dict[str, Any]], defaults: dict[str, Any] | None = None
) -> vol.Schema:
    """Baut das Formular für die Licht-/Klimaanlagen-Zuordnung.

    Eine Seite pro Licht-/Klimaanlagen-Eintrag im Seitenplan (statt
    früher fest einer Licht- und einer Klimaanlagen-Seite) - ein leer
    gelassener Licht-Slot wird beim Anlegen der Entities einfach
    übersprungen.
    """
    defaults = defaults or {}
    schema_dict: dict[Any, Any] = {}

    for page in [p for p in plan if p["type"] == "light"]:
        instance = page["instance"]
        for index in range(1, MAX_LIGHT_SLOTS + 1):
            entity_key = light_slot_entity_key(instance, index)
            name_key = light_slot_name_key(instance, index)
            schema_dict[
                vol.Optional(
                    entity_key,
                    description={"suggested_value": defaults.get(entity_key) or None},
                )
            ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="light"))
            schema_dict[
                vol.Optional(
                    name_key, default=defaults.get(name_key, f"Licht {index}")
                )
            ] = str

    for page in [p for p in plan if p["type"] == "climate"]:
        instance = page["instance"]
        key = climate_target_key(instance)
        schema_dict[
            vol.Optional(
                key, description={"suggested_value": defaults.get(key) or None}
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
    """Options-Flow: zuerst Seitenplan, danach Licht-/Klima-Zuordnung."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._new_plan: list[dict[str, Any]] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        current = {**self._config_entry.data, **self._config_entry.options}
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                parsed = json.loads(user_input["page_plan_json"])
                if not isinstance(parsed, list):
                    raise ValueError("page_plan_json muss eine Liste sein")
                for entry in parsed:
                    if not isinstance(entry, dict) or "type" not in entry:
                        raise ValueError("jeder Eintrag braucht mindestens 'type'")
                    if entry["type"] not in PAGE_TYPES:
                        raise ValueError(f"unbekannter Seitentyp: {entry['type']!r}")
            except (json.JSONDecodeError, ValueError):
                errors["base"] = "invalid_page_plan"
            else:
                self._new_plan = parsed
                return await self.async_step_entities()

        return self.async_show_form(
            step_id="init",
            data_schema=_page_plan_schema(get_page_plan(current)),
            errors=errors,
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        current = {**self._config_entry.data, **self._config_entry.options}
        plan = self._new_plan if self._new_plan is not None else get_page_plan(current)

        if user_input is not None:
            cleaned = {
                key: value
                for key, value in user_input.items()
                if value not in (None, "")
            }
            cleaned[CONF_PAGE_PLAN] = plan
            return self.async_create_entry(title="", data=cleaned)

        return self.async_show_form(
            step_id="entities",
            data_schema=_entity_mapping_schema(plan, current),
        )
