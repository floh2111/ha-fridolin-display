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

# Wie viele Licht-Slots die Integration anbietet. Der Übersichtlichkeit
# halber eine feste, großzügig bemessene Zahl statt einer dynamischen
# Liste - ein Slot ohne zugewiesene Entity wird einfach nicht angelegt.
MAX_LIGHT_SLOTS = 4

# ---- Config-/Options-Keys ----
CONF_DEVICE_TRACKER = "device_tracker_entity_id"
CONF_CLIMATE_TARGET = "climate_target_entity_id"
CONF_OWM_API_KEY = "owm_api_key"
CONF_OWM_UNITS = "owm_units"
CONF_OWM_LANG = "owm_lang"
CONF_LIGHT_SLOT_ENTITY = "light_slot_{index}_entity_id"
CONF_LIGHT_SLOT_NAME = "light_slot_{index}_name"

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
