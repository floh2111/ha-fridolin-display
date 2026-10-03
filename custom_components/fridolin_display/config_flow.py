"""Config- und Options-Flow für Fridolin Display.

Der Einrichtungsdialog (Config Flow) fragt einmalig nach dem
Standort-Tracker und dem OpenWeatherMap-API-Key. Über den
"Konfigurieren"-Button der Integration (Options Flow) lässt sich danach
jederzeit ändern:
  1. der Seitenplan (welche Seiten das Display in welcher Reihenfolge
     zeigt, siehe page_plan.py) - über ein Menü (Seite hinzufügen/
     entfernen/verschieben) oder als JSON-Liste für Experten. Eine
     Änderung der Seiten-*Auswahl/Reihenfolge* braucht ein neu
     generiertes + geflashtes Display (siehe esphome/generate_display_yaml.py,
     das auch den Diagnose-Export dieser Integration direkt einliest -
     Einstellungen -> Geräte & Dienste -> Fridolin Display -> ⋮ ->
     Diagnose herunterladen), eine Änderung *innerhalb* eines
     bestehenden Licht-/Klimaanlagen-Slots (welche echte Entity
     dahintersteckt) dagegen nicht.
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
    MAX_COVER_SLOTS,
    MAX_LIGHT_SLOTS,
    PAGE_TYPES,
    PAGE_TYPES_WITH_ENTITIES,
    cover_slot_entity_key,
    cover_slot_name_key,
    light_slot_entity_key,
    light_slot_name_key,
    climate_target_key,
)
from .page_plan import get_page_plan, normalize_page_plan

PAGE_TYPE_LABELS = {
    "overview": "Übersicht",
    "light": "Licht",
    "climate": "Klimaanlage",
    "leveling": "Nivellierung",
    "fridge": "Kühlbox",
    "sensors": "Sensoren (generisch)",
    "cover": "Rollläden",
}


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


def _page_plan_json_schema(current_plan: list[dict[str, Any]]) -> vol.Schema:
    """Seitenplan als JSON-Liste editierbar - Experten-Fallback neben dem
    Menü-gefuehrten Editor (async_step_manage_pages & Co.), z.B. um
    mehrere Seiten auf einmal zu aendern oder eine sensors-Seite mit
    vielen Entities bequem einzufuegen."""
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


def _add_page_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("type"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=t, label=PAGE_TYPE_LABELS[t])
                        for t in PAGE_TYPES
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required("title"): str,
            vol.Optional("instance", default=""): str,
            vol.Optional(
                "sensors_entities", default=[]
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
        }
    )


def _page_choice_schema(
    plan: list[dict[str, Any]], *, with_direction: bool
) -> vol.Schema:
    options = [
        selector.SelectOptionDict(
            value=str(i),
            label=f"{i + 1}. {p.get('title') or PAGE_TYPE_LABELS.get(p['type'], p['type'])} ({PAGE_TYPE_LABELS.get(p['type'], p['type'])})",
        )
        for i, p in enumerate(plan)
    ]
    schema_dict: dict[Any, Any] = {
        vol.Required("page_index"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
        ),
    }
    if with_direction:
        schema_dict[vol.Required("direction")] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="up", label="Nach oben"),
                    selector.SelectOptionDict(value="down", label="Nach unten"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    return vol.Schema(schema_dict)


def _format_plan_summary(plan: list[dict[str, Any]]) -> str:
    if not plan:
        return "(noch keine Seiten)"
    lines = []
    for i, page in enumerate(plan):
        type_label = PAGE_TYPE_LABELS.get(page["type"], page["type"])
        extra = ""
        if page["type"] in PAGE_TYPES_WITH_ENTITIES and page.get("instance"):
            extra = f", Instanz {page['instance']}"
        if page["type"] == "sensors":
            count = len(page.get("entities") or [])
            extra = f", {count} Sensor(en)"
        lines.append(f"{i + 1}. {page.get('title') or type_label} ({type_label}{extra})")
    return "\n".join(lines)


def _sensors_entities_from_selection(
    hass: Any, entity_ids: list[str]
) -> list[dict[str, str]]:
    """Baut die 'entities'-Liste einer sensors-Seite aus per EntitySelector
    ausgewaehlten Entity-IDs (kein manuelles Eintippen von Entity-ID/Label/
    Einheit mehr noetig, siehe _add_page_schema). Label = aktueller
    Anzeigename (State.name, i.d.R. der friendly_name), Einheit = aktuelle
    unit_of_measurement - beides zum Zeitpunkt der Auswahl aus dem State
    gelesen (Momentaufnahme, kein Live-Sync). Fehlt der State (z.B. Entity
    aktuell nicht verfuegbar), wird die Entity-ID selbst als Label
    verwendet. Ein individuell abweichendes Label laesst sich weiterhin nur
    ueber "Seitenplan als JSON bearbeiten" setzen."""
    entities: list[dict[str, str]] = []
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        label = (state.name if state else None) or entity_id
        unit = (state.attributes.get("unit_of_measurement") if state else None) or ""
        entities.append({"entity_id": entity_id, "label": label, "unit": unit})
    return entities


def _entity_mapping_schema(
    plan: list[dict[str, Any]], defaults: dict[str, Any] | None = None
) -> vol.Schema:
    """Baut das Formular für die Licht-/Klimaanlagen-Zuordnung.

    Eine Seite pro Licht-/Klimaanlagen-Eintrag im Seitenplan - ein leer
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
            ] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["light", "switch"]))
            schema_dict[
                vol.Optional(
                    name_key, default=defaults.get(name_key, f"Licht {index}")
                )
            ] = str

    for page in [p for p in plan if p["type"] == "cover"]:
        instance = page["instance"]
        for index in range(1, MAX_COVER_SLOTS + 1):
            entity_key = cover_slot_entity_key(instance, index)
            name_key = cover_slot_name_key(instance, index)
            schema_dict[
                vol.Optional(
                    entity_key,
                    description={"suggested_value": defaults.get(entity_key) or None},
                )
            ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="cover"))
            schema_dict[
                vol.Optional(
                    name_key, default=defaults.get(name_key, f"Rollladen {index}")
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
    """Options-Flow: Hauptmenü -> Seiten verwalten (Menü-Editor) /
    Seitenplan als JSON (Experten) / Entity-Zuordnung + Speichern."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._working_plan: list[dict[str, Any]] | None = None

    def _current_config(self) -> dict[str, Any]:
        return {**self._config_entry.data, **self._config_entry.options}

    def _plan(self) -> list[dict[str, Any]]:
        if self._working_plan is None:
            self._working_plan = get_page_plan(self._current_config())
        return self._working_plan

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        self._plan()  # stellt sicher, dass _working_plan initialisiert ist
        return self.async_show_menu(
            step_id="init",
            menu_options=["manage_pages", "edit_json", "entities"],
        )

    # ---- Seiten verwalten (Menü-gefuehrter Editor) ----

    async def async_step_manage_pages(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        return self.async_show_menu(
            step_id="manage_pages",
            menu_options=["add_page", "remove_page", "move_page", "init"],
            description_placeholders={"plan_summary": _format_plan_summary(self._plan())},
        )

    async def async_step_add_page(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            page_type = user_input["type"]
            title = user_input["title"].strip() or PAGE_TYPE_LABELS.get(page_type, page_type)
            new_page: dict[str, Any] = {"type": page_type, "title": title}

            if page_type in PAGE_TYPES_WITH_ENTITIES:
                instance = user_input.get("instance", "").strip()
                if instance:
                    new_page["instance"] = instance
                # sonst vergibt page_plan.py beim naechsten get_page_plan()
                # automatisch eine freie Instanz-Nummer

            if page_type == "sensors":
                new_page["entities"] = _sensors_entities_from_selection(
                    self.hass, user_input.get("sensors_entities") or []
                )

            self._plan().append(new_page)
            self._working_plan = normalize_page_plan(self._working_plan)
            return await self.async_step_manage_pages()

        return self.async_show_form(
            step_id="add_page",
            data_schema=_add_page_schema(),
            errors=errors,
        )

    async def async_step_remove_page(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        plan = self._plan()
        if not plan:
            return await self.async_step_manage_pages()

        if user_input is not None:
            index = int(user_input["page_index"])
            if 0 <= index < len(plan):
                plan.pop(index)
            return await self.async_step_manage_pages()

        return self.async_show_form(
            step_id="remove_page",
            data_schema=_page_choice_schema(plan, with_direction=False),
        )

    async def async_step_move_page(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        plan = self._plan()
        if len(plan) < 2:
            return await self.async_step_manage_pages()

        if user_input is not None:
            index = int(user_input["page_index"])
            direction = user_input["direction"]
            target = index - 1 if direction == "up" else index + 1
            if 0 <= index < len(plan) and 0 <= target < len(plan):
                plan[index], plan[target] = plan[target], plan[index]
            return await self.async_step_manage_pages()

        return self.async_show_form(
            step_id="move_page",
            data_schema=_page_choice_schema(plan, with_direction=True),
        )

    # ---- Seitenplan als JSON (Experten-Fallback) ----

    async def async_step_edit_json(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
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
                self._working_plan = normalize_page_plan(parsed)
                return await self.async_step_init()

        return self.async_show_form(
            step_id="edit_json",
            data_schema=_page_plan_json_schema(self._plan()),
            errors=errors,
        )

    # ---- Entity-Zuordnung + Speichern ----

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        current = self._current_config()
        plan = self._plan()

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
