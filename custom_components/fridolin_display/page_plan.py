"""Seitenplan: welche Seiten das Display in welcher Reihenfolge zeigt.

Der Plan ist eine Liste von Dicts (siehe DEFAULT_PAGE_PLAN in const.py),
in den Integrations-Optionen als geparstes JSON gespeichert (Schlüssel
CONF_PAGE_PLAN). Diese Datei buendelt das Einlesen/Normalisieren, damit
light.py, climate.py und der YAML-Generator (esphome/generate_display_yaml.py)
denselben Code nutzen statt den Plan jeweils eigenstaendig zu interpretieren.
"""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_PAGE_PLAN,
    DEFAULT_PAGE_PLAN,
    LEGACY_INSTANCE,
    PAGE_TYPES,
    PAGE_TYPES_WITH_ENTITIES,
)


def get_page_plan(config: dict[str, Any]) -> list[dict[str, str]]:
    """Liest + normalisiert den Seitenplan aus der Config.

    Fehlt er (ältere Installation, die den Seitenplan noch nicht selbst
    gesetzt hat), wird DEFAULT_PAGE_PLAN verwendet - das entspricht dem
    bisherigen, fest verdrahteten 5-Seiten-Display.
    """
    raw = config.get(CONF_PAGE_PLAN) or DEFAULT_PAGE_PLAN
    return normalize_page_plan(raw)


def normalize_page_plan(raw: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Normalisiert eine rohe Seitenplan-Liste (fehlende 'instance' wird
    vergeben, 'entities' einer sensors-Seite vereinheitlicht, unbekannte
    Typen rausgefiltert). Oeffentlich, damit config_flow.py sie nach jeder
    Menü-Änderung (Seite hinzufügen/entfernen/verschieben) erneut aufrufen
    kann - sonst fehlt einer frisch hinzugefügten Seite z.B. 'instance'."""
    plan: list[dict[str, str]] = []
    # Zaehlt, die wievielte Seite dieses Typs wir gerade sehen, um eine
    # fehlende "instance" automatisch zu vergeben (1, 2, 3, ...) - die
    # erste Instanz eines Typs bekommt LEGACY_INSTANCE, damit ein Plan
    # ohne explizite instance-Angabe genau dem alten Verhalten entspricht.
    seen_of_type: dict[str, int] = {}

    for entry in raw:
        page_type = entry.get("type")
        if page_type not in PAGE_TYPES:
            continue  # unbekannter/kaputter Eintrag wird stillschweigend übersprungen

        normalized: dict[str, str] = {
            "type": page_type,
            "title": str(entry.get("title") or page_type.capitalize()),
        }

        if page_type in PAGE_TYPES_WITH_ENTITIES:
            count = seen_of_type.get(page_type, 0) + 1
            seen_of_type[page_type] = count
            instance = str(entry.get("instance") or "")
            if not instance:
                instance = LEGACY_INSTANCE if count == 1 else str(count)
            normalized["instance"] = instance

        if page_type == "sensors":
            normalized["entities"] = _normalize_sensor_entities(entry.get("entities"))  # type: ignore[assignment]

        plan.append(normalized)

    return plan


def _normalize_sensor_entities(raw: Any) -> list[dict[str, str]]:
    """Normalisiert die 'entities'-Liste einer sensors-Seite.

    Jeder Eintrag ist entweder eine blosse Entity-ID (String, z.B.
    "sensor.batterie_soc" - label wird dann von der Entity-ID abgeleitet)
    oder ein Objekt {"entity_id", "label"?, "unit"?} - "label" ist der
    Zeilentext auf dem Display, "unit" wird hinter den Rohwert der
    HA-Entity gehaengt (ESPHome kennt die Einheit der Ziel-Entity zur
    Kompilierzeit nicht, siehe esphome/generate_display_yaml.py).
    """
    if not isinstance(raw, list):
        return []
    entities: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            entity_id = item
            label = entity_id
            unit = ""
        elif isinstance(item, dict):
            entity_id = str(item.get("entity_id") or "")
            if not entity_id:
                continue
            label = str(item.get("label") or entity_id)
            unit = str(item.get("unit") or "")
        else:
            continue
        entities.append({"entity_id": entity_id, "label": label, "unit": unit})
    return entities


def light_pages(config: dict[str, Any]) -> list[dict[str, str]]:
    """Alle Licht-Seiten im Plan (jede mit eigener 'instance')."""
    return [p for p in get_page_plan(config) if p["type"] == "light"]


def climate_pages(config: dict[str, Any]) -> list[dict[str, str]]:
    """Alle Klimaanlagen-Seiten im Plan (jede mit eigener 'instance')."""
    return [p for p in get_page_plan(config) if p["type"] == "climate"]


def cover_pages(config: dict[str, Any]) -> list[dict[str, str]]:
    """Alle Rollladen-Seiten im Plan (jede mit eigener 'instance')."""
    return [p for p in get_page_plan(config) if p["type"] == "cover"]
