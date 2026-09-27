"""Diagnose-Export für Fridolin Display.

Nutzt Home Assistants eingebauten "Diagnose herunterladen"-Knopf
(Einstellungen → Geräte & Dienste → Fridolin Display → ⋮) - kein
eigenes UI nötig. Enthält u.a. den aktuellen Seitenplan als fertiges
JSON, das sich direkt an esphome/generate_display_yaml.py --plan
übergeben lässt (das Skript erkennt sowohl die rohe Seitenplan-Liste
als auch diesen Diagnose-Dump mit "page_plan"-Schlüssel, siehe dort).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .page_plan import get_page_plan

# Zugangsdaten/persönliche Standortdaten nie im Diagnose-Export ausgeben
TO_REDACT = {"owm_api_key", "device_tracker_entity_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Diagnose-Daten für einen Config Entry zusammenstellen."""
    config = {**entry.data, **entry.options}
    return {
        "page_plan": get_page_plan(config),
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": async_redact_data(dict(entry.options), TO_REDACT),
    }
