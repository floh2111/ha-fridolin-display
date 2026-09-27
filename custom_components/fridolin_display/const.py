"""Konstanten für die Fridolin-Display-Integration.

Diese Integration ist die Gegenstelle zum Touch-Display im Wohnwagen
(ESP32 + ESPHome/LVGL). Das Display spricht immer nur mit einer festen
Handvoll Entities dieser Integration (z.B. light.fridolin_licht_1,
climate.fridolin_heizung, sensor.fridolin_wetter_zustand). Welche
"echten" Entities dahinterstecken, stellst du hier über die normale
Home-Assistant-Oberfläche ein (Einstellungen -> Geräte & Dienste ->
Fridolin Display -> Konfigurieren) - ohne den ESP32 neu flashen zu
müssen.
"""

from __future__ import annotations

DOMAIN = "fridolin_display"

MANUFACTURER = "Selbstbau"
MODEL = "Fridolin Touch-Display (Waveshare ESP32-S3-Touch-LCD-7)"

# Wie viele Licht-Slots eine einzelne Licht-Seite anbietet. Der
# Übersichtlichkeit halber eine feste, großzügig bemessene Zahl statt
# einer dynamischen Liste - ein Slot ohne zugewiesene Entity wird einfach
# nicht angelegt.
MAX_LIGHT_SLOTS = 4

# Instanz-Kennung der jeweils ersten Licht-/Klimaanlagen-Seite im
# Seitenplan: bekommt bewusst die *alten*, seit Version 0.1.x
# bestehenden Entity-IDs (light.fridolin_licht_1.._4,
# climate.fridolin_heizung) statt der neuen instanz-parametrisierten
# Namen - damit bestehende Dashboards/Automationen beim Umstieg auf den
# Seitenplan nicht brechen. Nur *weitere* Instanzen (z.B. eine zweite
# Klimazone) bekommen neue, instanz-parametrisierte IDs.
LEGACY_INSTANCE = "1"

# ---- Seitenplan (welche Seiten das Display in welcher Reihenfolge
# zeigt) ----
CONF_PAGE_PLAN = "page_plan"

PAGE_TYPE_OVERVIEW = "overview"
PAGE_TYPE_LIGHT = "light"
PAGE_TYPE_CLIMATE = "climate"
PAGE_TYPE_LEVELING = "leveling"
PAGE_TYPE_FRIDGE = "fridge"
PAGE_TYPE_SENSORS = "sensors"

# overview/leveling/fridge sind lokale bzw. Einzel-Seiten (Kühlbox und
# Nivellierung sprechen direkt mit dem ESP, nicht mit dieser
# Integration) - fuer sie legt diese Integration keine Entities an,
# nur light/climate/sensors erzeugen Display-Entities pro Instanz.
PAGE_TYPES = [
    PAGE_TYPE_OVERVIEW,
    PAGE_TYPE_LIGHT,
    PAGE_TYPE_CLIMATE,
    PAGE_TYPE_LEVELING,
    PAGE_TYPE_FRIDGE,
    PAGE_TYPE_SENSORS,
]
PAGE_TYPES_WITH_ENTITIES = {PAGE_TYPE_LIGHT, PAGE_TYPE_CLIMATE, PAGE_TYPE_SENSORS}

# Seitenplan, der dem bisherigen, fest verdrahteten Display entspricht -
# Vorbelegung fuer bestehende Installationen, die den Seitenplan noch
# nicht selbst angelegt haben.
DEFAULT_PAGE_PLAN: list[dict[str, str]] = [
    {"type": PAGE_TYPE_OVERVIEW, "title": "Übersicht"},
    {"type": PAGE_TYPE_LIGHT, "title": "Licht", "instance": LEGACY_INSTANCE},
    {"type": PAGE_TYPE_CLIMATE, "title": "Klimaanlage", "instance": LEGACY_INSTANCE},
    {"type": PAGE_TYPE_LEVELING, "title": "Nivellierung"},
    {"type": PAGE_TYPE_FRIDGE, "title": "Kühlbox"},
]

# ---- Config-/Options-Keys ----
CONF_DEVICE_TRACKER = "device_tracker_entity_id"
CONF_OWM_API_KEY = "owm_api_key"
CONF_OWM_UNITS = "owm_units"
CONF_OWM_LANG = "owm_lang"

# {instance} ist LEGACY_INSTANCE ("1") fuer die erste Licht-/Klimaseite
# im Plan (siehe oben) - dort bewusst dieselben Schluessel wie vor dem
# Seitenplan, damit bestehende Konfigurationen erhalten bleiben.
CONF_CLIMATE_TARGET = "climate_target_{instance}_entity_id"
CONF_LIGHT_SLOT_ENTITY = "light_{instance}_slot_{index}_entity_id"
CONF_LIGHT_SLOT_NAME = "light_{instance}_slot_{index}_name"

# Legacy-Schluessel (instance == LEGACY_INSTANCE), unveraendert seit
# 0.1.x - fuer die Migration alter Configs auf das neue, instanz-
# parametrisierte Schema.
LEGACY_CONF_CLIMATE_TARGET = "climate_target_entity_id"
LEGACY_CONF_LIGHT_SLOT_ENTITY = "light_slot_{index}_entity_id"
LEGACY_CONF_LIGHT_SLOT_NAME = "light_slot_{index}_name"

DEFAULT_OWM_UNITS = "metric"
DEFAULT_OWM_LANG = "de"
DEFAULT_NAME = "Fridolin Display"

# Update-Intervalle
WEATHER_UPDATE_INTERVAL_MINUTES = 15

# Home-Zone als Fallback-Standort, solange noch nie "Standort übernehmen"
# gedrückt wurde
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def climate_target_key(instance: str) -> str:
    """Config-Key fuer die Ziel-climate-Entity einer Klimaanlagen-Seite.

    instance == LEGACY_INSTANCE liefert den alten, seit 0.1.x
    unveraenderten Schluessel (siehe LEGACY_CONF_CLIMATE_TARGET), jede
    weitere Instanz einen neuen, instanz-parametrisierten Schluessel.
    """
    if instance == LEGACY_INSTANCE:
        return LEGACY_CONF_CLIMATE_TARGET
    return CONF_CLIMATE_TARGET.format(instance=instance)


def light_slot_entity_key(instance: str, index: int) -> str:
    """Config-Key fuer die Ziel-light-Entity eines Licht-Slots."""
    if instance == LEGACY_INSTANCE:
        return LEGACY_CONF_LIGHT_SLOT_ENTITY.format(index=index)
    return CONF_LIGHT_SLOT_ENTITY.format(instance=instance, index=index)


def light_slot_name_key(instance: str, index: int) -> str:
    """Config-Key fuer den Anzeigenamen eines Licht-Slots."""
    if instance == LEGACY_INSTANCE:
        return LEGACY_CONF_LIGHT_SLOT_NAME.format(index=index)
    return CONF_LIGHT_SLOT_NAME.format(instance=instance, index=index)


def climate_entity_id(instance: str) -> str:
    """Feste Display-Entity-ID der Klimaanlagen-Seite dieser Instanz."""
    if instance == LEGACY_INSTANCE:
        return "climate.fridolin_heizung"
    return f"climate.fridolin_climate_{instance}"


def light_entity_id(instance: str, index: int) -> str:
    """Feste Display-Entity-ID eines Licht-Slots dieser Instanz."""
    if instance == LEGACY_INSTANCE:
        return f"light.fridolin_licht_{index}"
    return f"light.fridolin_licht_{instance}_{index}"
