#!/usr/bin/env python3
"""Erzeugt wohnwagen-display.yaml aus einem Seitenplan.

Nimmt den Seitenplan der Fridolin-Display-Integration (siehe
custom_components/fridolin_display/page_plan.py, gleiches JSON-Format)
und baut daraus eine wohnwagen-display.yaml mit genau den gewuenschten
Seiten in der gewuenschten Reihenfolge/mit den gewuenschten Titeln.

Funktionsweise: wohnwagen-display.yaml selbst dient als "Block-Bibliothek".
Die fuenf Seiten-Bloecke (tile_uebersicht/tile_licht/tile_heizung/
tile_nivellierung/tile_kuehlbox) innerhalb der lvgl: -> pages: -> tiles:
Liste werden per Markierungs-Zeilen ("- id: tile_xxx", plus die
Kommentarzeilen direkt davor) erkannt und als Rohtext extrahiert und laut
Plan neu zusammengesetzt (Reihenfolge/Titel).

Fehlt ein Seitentyp im Plan (light/climate/fridge - siehe
REMOVE_ITEM_ANCHORS/STRIP_SUBKEY_ANCHORS), werden zusaetzlich dessen im
Rest der Datei VERSTREUTE Definitionen entfernt (HA-Spiegel-Sensoren,
Sync-Scripts, bei fridge die komplette Tuya-BLE-Anbindung) - sonst
referenzieren sie nach dem Entfernen des tile_*-Blocks nicht mehr
existierende Widget-IDs (Compile-Fehler). overview und leveling muessen
weiterhin immer im Plan enthalten sein (siehe REQUIRED_PAGE_TYPES fuer
die Begruendung). Alles andere in der Datei (Hardware, WLAN,
Wetter-System, Einstellungen-Overlay, Bild-Assets, ...) bleibt
unveraendert. Siehe CLAUDE.md, "Seitenplan / Seiten-Baukasten" fuer den
genauen Stand/die Grenzen.

Aufruf:
    python3 generate_display_yaml.py --plan page_plan.json --out wohnwagen-display.yaml
    python3 generate_display_yaml.py --check   # Round-Trip-Selbsttest (siehe unten)

--check baut aus wohnwagen-display.yaml selbst einen Seitenplan, der die
Reihenfolge/Titel exakt widerspiegelt, generiert daraus erneut eine Datei
und vergleicht sie Byte fuer Byte mit dem Original - das validiert den
Parser, ohne dass ein separater Seitenplan gepflegt werden muss.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SOURCE_FILE = Path(__file__).parent / "wohnwagen-display.yaml"

TILE_ID_BY_TYPE = {
    "overview": "tile_uebersicht",
    "light": "tile_licht",
    "climate": "tile_heizung",
    "leveling": "tile_nivellierung",
    "fridge": "tile_kuehlbox",
}
TYPE_BY_TILE_ID = {v: k for k, v in TILE_ID_BY_TYPE.items()}

# Einrueckung von "- id: tile_xxx" in der pages: -> tiles:-Liste. Wird auch
# benutzt, um das Ende des letzten Blocks (= Ende der tiles:-Liste) zu
# erkennen: die naechste nicht-leere Zeile mit WENIGER Einrueckung markiert
# das Ende (z.B. "  top_layer:").
TILE_INDENT = " " * 14

TITLE_LINE_RE = re.compile(r'^(\s*text:\s*)"([^"]*)"(\s*)$')
COLUMN_LINE_RE = re.compile(r"^(\s*column:\s*)\d+(\s*)$")

# Einrueckung, auf der die Top-Level-Listenelemente in Sektionen wie
# select:/number:/switch:/sensor:/text_sensor:/script:/button:/
# tuya_ble_node: beginnen ("  - platform: ..." bzw. "  - id: ...").
ITEM_INDENT = 2

# Seitentypen, die nicht in overview/leveling behandelt werden (siehe
# unten), haben neben ihrem tile_*-Block noch weitere, im Rest der Datei
# VERSTREUTE Definitionen (HA-Spiegel-Sensoren + Sync-Script fuer light/
# climate; die komplette Tuya-BLE-Anbindung fuer fridge) - die referenzieren
# Widget-IDs aus dem jeweiligen tile_*-Block und muessen mit entfernt
# werden, wenn die Seite im Plan fehlt, sonst "Couldn't find ID" beim
# Kompilieren. Jeder Eintrag ist eine Regex, die IRGENDEINE Zeile
# innerhalb des zu entfernenden Elements eindeutig identifiziert - das
# umschliessende Element (naechste "  - " Zeile davor, naechstes
# Element/Sektionsende danach) wird automatisch ermittelt (siehe
# _find_item_bounds).
# Bewusst exakt 4 Leerzeichen (Einrueckung eines direkten Feldes eines
# Listen-Elements, "  - platform: x" + "    id: y") statt "\s*" - manche
# dieser IDs tauchen auch VERSCHACHTELT in Lambdas/Aktionen anderer
# Elemente auf (z.B. "id: kb_ziel" innerhalb von kb_ziel_auswahl's
# set_action), "\s*" wuerde dort faelschlich zuschlagen und auf das
# falsche (umschliessende) Element zurueckfallen.
_FIELD_INDENT = " " * (ITEM_INDENT + 2)

# Einrueckung der beiden Wohnwagen/Wohnmobil-Umschalter-Widgets im
# Einstellungen-Overlay (Footer) - siehe REMOVE_ITEM_ANCHORS["leveling"].
# 18 statt (wie urspruenglich) 12, seit die Einstellungen-Seite einen
# umschliessenden Flex-COLUMN-Container bekommen hat (siehe
# wohnwagen-display.yaml, "top_layer:" -> overlay_einstellungen) - das
# fuegt eine zusaetzliche widgets:-Verschachtelungsebene ein. Bei
# sichtbaren Aenderungen an dieser Seite IMMER pruefen, ob sich die
# Einrueckung dieser beiden Anker-Zeilen mitverschoben hat (siehe
# CLAUDE.md, "Der YAML-Generator hat eigene, hartkodierte Text-Anker").
_SETTINGS_WIDGET_INDENT = 18

# Jeder Eintrag: (Regex, die IRGENDEINE Zeile innerhalb des zu entfernenden
# Elements eindeutig identifiziert, Einrueckung des umschliessenden "- "-
# Listen-Elements). Das umschliessende Element (naechste "- "-Zeile in
# dieser Einrueckung davor, naechstes Element/Sektionsende danach) wird
# automatisch ermittelt (siehe _find_item_bounds). Bewusst exakte
# Einrueckungen statt "\s*" bei Feldern wie "id:" - manche dieser IDs
# tauchen auch VERSCHACHTELT in Lambdas/Aktionen anderer Elemente auf
# (z.B. "id: kb_ziel" innerhalb von kb_ziel_auswahl's set_action), "\s*"
# wuerde dort faelschlich zuschlagen und auf das falsche (umschliessende)
# Element zurueckfallen.
REMOVE_ITEM_ANCHORS: dict[str, list[tuple[re.Pattern, int]]] = {
    "light": [(re.compile(rf"^{_FIELD_INDENT}id: ha_licht_{n}\s*$"), ITEM_INDENT) for n in range(1, 5)]
    + [(re.compile(r"^\s*- id: sync_lichter\s*$"), ITEM_INDENT)],
    "climate": [
        (re.compile(rf"^{_FIELD_INDENT}id: ha_heizung_modus\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: ha_klima_preset\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: ha_zieltemperatur\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: ha_klima_ist\s*$"), ITEM_INDENT),
        (re.compile(r"^\s*- id: sync_klima\s*$"), ITEM_INDENT),
    ],
    "fridge": [
        (re.compile(r"^\s*- id: g_kb_letzte\s*$"), ITEM_INDENT),  # Global, nur fuer die Kühlbox-Anzeige
        (re.compile(r"^\s*- id: kuehlbox\s*$"), ITEM_INDENT),  # tuya_ble_node: Geraet selbst
        (re.compile(rf"^{_FIELD_INDENT}id: kb_modus_sel\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: kb_batt_sel\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: kb_ziel_auswahl\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: kb_ziel\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: kb_power\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: kb_ist\s*$"), ITEM_INDENT),
        (re.compile(rf'^{_FIELD_INDENT}name: "Kühlbox Batterie"\s*$'), ITEM_INDENT),
        (re.compile(rf'^{_FIELD_INDENT}name: "Kühlbox Spannung"\s*$'), ITEM_INDENT),
        (re.compile(r"^\s*- id: sync_kuehlbox\s*$"), ITEM_INDENT),
        # interval:-Trigger, der sync_kuehlbox alle 10s aufruft (eigenes,
        # von "id: sync_kuehlbox" getrenntes Element - siehe interval:-
        # Sektion; "10s" ist an dieser Stelle eindeutig)
        (re.compile(r"^\s*- interval: 10s\s*$"), ITEM_INDENT),
    ],
    "leveling": [
        # Header: Fahrzeugtyp-Global, Wohnmobil-Bild-Asset, Umschalt-Script -
        # alle drei ergeben ohne die Nivellierungs-Seite keinen Sinn mehr.
        (re.compile(r"^\s*- id: g_fahrzeugtyp_wohnmobil\s*$"), ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: img_wohnmobil\s*$"), ITEM_INDENT),
        (re.compile(r"^\s*- id: sync_fahrzeugtyp\s*$"), ITEM_INDENT),
        # Footer: die beiden Umschalt-Widgets im Einstellungen-Overlay
        # (Label + der obj mit den beiden Knoepfen) - siehe
        # _SETTINGS_WIDGET_INDENT.
        (
            re.compile(r'^\s*text: "Fahrzeugtyp für die Nivellierungs-Seite:"\s*$'),
            _SETTINGS_WIDGET_INDENT,
        ),
        (re.compile(r"^\s*id: btn_fahrzeug_wohnwagen\s*$"), _SETTINGS_WIDGET_INDENT),
    ],
}

# Nivellierung ist zusaetzlich ein Sonderfall: die beiden Neigungs-Sensoren
# (neigung_links_rechts/neigung_vorne_hinten) speisen auch die
# HA-Sensor-Entities hinter der Lovelace-Karte (rv-leveling-card) - die
# sollen unabhaengig von der Display-Seite weiter funktionieren. Nur ihr
# on_value:-Unterblock (der die tile_nivellierung-Widgets aktualisiert)
# wird entfernt, nicht der ganze Sensor.
STRIP_SUBKEY_ANCHORS: dict[str, list[tuple[re.Pattern, str, int]]] = {
    "leveling": [
        (re.compile(rf"^{_FIELD_INDENT}id: neigung_links_rechts\s*$"), "on_value", ITEM_INDENT),
        (re.compile(rf"^{_FIELD_INDENT}id: neigung_vorne_hinten\s*$"), "on_value", ITEM_INDENT),
    ],
}

# Bare "key:"-Bloecke (keine "- "-Listen-Elemente) mit eigenem
# verschachteltem Inhalt, die komplett entfernt werden, wenn der
# Seitentyp fehlt. Jeder Eintrag: (Regex fuer die Block-Kopfzeile selbst,
# ihre Einrueckung).
REMOVE_KEY_BLOCK_ANCHORS: dict[str, list[tuple[re.Pattern, int]]] = {
    # on_boot: wendet nach dem Hochfahren nur den gespeicherten
    # Fahrzeugtyp auf die Nivellierungs-Seite an - ohne die Seite
    # ueberfluessig.
    "leveling": [(re.compile(r"^  on_boot:\s*$"), 2)],
}

# Fuer Mehrfach-Instanzen (2., 3., ... Licht-/Klimaanlagen-Seite):
# dieselben Fragmente wie REMOVE_ITEM_ANCHORS, zusaetzlich annotiert mit
# der Ziel-Sektion, in die eine instanz-suffixierte Kopie eingefuegt
# werden muss (text_sensor:/sensor:/script: - climate ist auf alle drei
# verteilt). Siehe render_extra_instance().
# Instanz-Kennung der ersten (unsuffixierten) light/climate-Seite - muss
# zum gleichnamigen Wert in custom_components/fridolin_display/const.py
# passen.
LEGACY_INSTANCE = "1"

MULTI_INSTANCE_SECTIONS: dict[str, list[tuple[re.Pattern, int, str]]] = {
    "light": [
        (re.compile(rf"^{_FIELD_INDENT}id: ha_licht_{n}\s*$"), ITEM_INDENT, "text_sensor")
        for n in range(1, 5)
    ]
    + [(re.compile(r"^\s*- id: sync_lichter\s*$"), ITEM_INDENT, "script")],
    "climate": [
        (re.compile(rf"^{_FIELD_INDENT}id: ha_heizung_modus\s*$"), ITEM_INDENT, "text_sensor"),
        (re.compile(rf"^{_FIELD_INDENT}id: ha_klima_preset\s*$"), ITEM_INDENT, "text_sensor"),
        (re.compile(rf"^{_FIELD_INDENT}id: ha_zieltemperatur\s*$"), ITEM_INDENT, "sensor"),
        (re.compile(rf"^{_FIELD_INDENT}id: ha_klima_ist\s*$"), ITEM_INDENT, "sensor"),
        (re.compile(r"^\s*- id: sync_klima\s*$"), ITEM_INDENT, "script"),
    ],
}

# Seitentypen, deren verstreute Abhaengigkeiten (noch) nicht erfasst sind -
# ein Plan ohne diese Typen wird abgelehnt statt eine kaputte Datei zu
# erzeugen. overview hat ein komplettes Wettersystem, Uhrzeit und Standort
# als Abhaengigkeiten - viele, wenig klar abgrenzbare Fragmente, ausserdem
# ist es die "Startseite" (ein Plan ohne sie ist ein Sonderfall, der
# bisher als nicht sinnvoll eingestuft wurde, siehe CLAUDE.md).
REQUIRED_PAGE_TYPES = {"overview"}


class ParseError(RuntimeError):
    pass


def split_source(text: str) -> tuple[str, dict[str, str], str]:
    """Zerlegt die Quelldatei in (header, {page_type: block_text}, footer)."""
    lines = text.splitlines(keepends=True)
    tile_start_re = re.compile(rf"^{TILE_INDENT}- id: (tile_\w+)\s*$")

    tile_line_indices = [i for i, line in enumerate(lines) if tile_start_re.match(line)]
    if len(tile_line_indices) != len(TILE_ID_BY_TYPE):
        raise ParseError(
            f"Erwartete {len(TILE_ID_BY_TYPE)} Seiten-Bloecke in {SOURCE_FILE.name}, "
            f"gefunden: {len(tile_line_indices)}. Die Datei wurde vermutlich so "
            "veraendert, dass der Generator sie nicht mehr sicher zerlegen kann - "
            "bitte die TILE_ID_BY_TYPE-Zuordnung und die Block-Erkennung in diesem "
            "Skript pruefen."
        )
    tile_ids = [tile_start_re.match(lines[i]).group(1) for i in tile_line_indices]
    unknown = set(tile_ids) - set(TYPE_BY_TILE_ID)
    if unknown:
        raise ParseError(f"Unbekannte Tile-IDs gefunden: {sorted(unknown)}")

    # Jeder Block beginnt bei seinen eigenen fuehrenden "###"-Kommentarzeilen
    # (falls vorhanden), nicht erst beim "- id: tile_xxx" selbst - so wandert
    # die Beschreibung mit, wenn eine Seite verschoben/entfernt wird.
    block_starts: list[int] = []
    for idx in tile_line_indices:
        start = idx
        j = idx - 1
        while j >= 0 and lines[j].lstrip().startswith("###"):
            start = j
            j -= 1
        block_starts.append(start)

    header = "".join(lines[: block_starts[0]])

    # Ende des letzten Blocks = Ende der tiles:-Liste = naechste nicht-leere
    # Zeile mit weniger Einrueckung als TILE_INDENT.
    last_tile_idx = tile_line_indices[-1]
    footer_start = None
    for i in range(last_tile_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent < len(TILE_INDENT):
            footer_start = i
            break
    if footer_start is None:
        raise ParseError("Konnte das Ende der tiles:-Liste nicht finden (kein Footer?)")

    boundaries = block_starts + [footer_start]
    blocks: dict[str, str] = {}
    for n in range(len(tile_line_indices)):
        tile_id = tile_ids[n]
        page_type = TYPE_BY_TILE_ID[tile_id]
        block_text = "".join(lines[boundaries[n] : boundaries[n + 1]])
        blocks[page_type] = block_text

    footer = "".join(lines[footer_start:])
    return header, blocks, footer


def set_column(block_text: str, column: int) -> str:
    """Setzt den 'column:'-Wert des Tiles (Position im Wisch-Karussell)."""
    lines = block_text.splitlines(keepends=True)
    replaced = False
    for i, line in enumerate(lines):
        m = COLUMN_LINE_RE.match(line)
        if m:
            lines[i] = f"{m.group(1)}{column}{m.group(2)}"
            replaced = True
            break
    if not replaced:
        raise ParseError("Block hat keine 'column:'-Zeile - Format geaendert?")
    return "".join(lines)


def set_title(block_text: str, title: str) -> str:
    """Ersetzt die erste 'text: \"...\"'-Zeile (die Seitenueberschrift).

    Betrifft nur light/climate/leveling/fridge - die Uebersichtsseite hat
    keine einzelne Titel-Zeile in diesem Muster (eigenes Layout mit
    Wetter/Uhrzeit/Zahnrad-Button) und wird nicht angefasst.
    """
    lines = block_text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = TITLE_LINE_RE.match(line)
        if m:
            escaped = title.replace('"', '\\"')
            lines[i] = f'{m.group(1)}"{escaped}"{m.group(3)}'
            return "".join(lines)
    raise ParseError("Block hat keine Titel-Zeile (text: \"...\") gefunden")


def _yaml_dq(text: str) -> str:
    """Escaped Text fuer eine doppelt-gequotete YAML-Zeichenkette."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def render_sensors_tile(page: dict, column: int, page_index: int) -> str:
    """Baut den tile_*-Block einer generischen Sensor-Seite (Seitentyp
    'sensors'). Anders als die anderen Seitentypen NICHT aus der
    Block-Bibliothek kopiert, sondern aus der 'entities'-Liste des
    Plan-Eintrags frisch gerendert - die Anzahl/Auswahl der Sensoren ist
    beliebig, dafuer gibt es keinen festen vorkompilierten Block."""
    title = _yaml_dq(page.get("title") or "Sensoren")
    entities = page.get("entities") or []

    if entities:
        rows = "".join(
            f'                        - obj:\n'
            f'                            width: 560\n'
            f'                            height: 50\n'
            f'                            radius: 12\n'
            f'                            bg_color: 0x1D2733\n'
            f'                            border_color: 0x3A4250\n'
            f'                            border_width: 2\n'
            f'                            pad_left: 20\n'
            f'                            pad_right: 20\n'
            f'                            layout: {{ type: FLEX, flex_flow: ROW, flex_align_main: SPACE_BETWEEN, flex_align_cross: CENTER }}\n'
            f'                            widgets:\n'
            f'                              - label:\n'
            f'                                  text: "{_yaml_dq(ent.get("label") or ent.get("entity_id", ""))}"\n'
            f'                                  text_font: fridolin_20\n'
            f'                              - label:\n'
            f'                                  id: lbl_sensorseite_{page_index}_{i}\n'
            f'                                  text: "--"\n'
            f'                                  text_font: fridolin_20\n'
            for i, ent in enumerate(entities)
        )
    else:
        rows = (
            '                        - label:\n'
            '                            text: "Keine Sensoren eingerichtet"\n'
            '                            text_font: fridolin_14\n'
        )

    return (
        f'              ### Seite "{title}" (generische Sensor-Anzeige, per Seitenplan erzeugt)\n'
        f'              - id: tile_sensorseite_{page_index}\n'
        f'                row: 0\n'
        f'                column: {column}\n'
        f'                dir: HOR\n'
        f'                widgets:\n'
        f'                  - label:\n'
        f'                      text: "{title}"\n'
        f'                      text_font: fridolin_28\n'
        f'                      align: TOP_MID\n'
        f'                      y: 16\n'
        f'                  - obj:\n'
        f'                      align: CENTER\n'
        f'                      y: 10\n'
        f'                      width: 600\n'
        f'                      height: 360\n'
        f'                      bg_opa: TRANSP\n'
        f'                      border_opa: TRANSP\n'
        f'                      layout: {{ type: FLEX, flex_flow: COLUMN, flex_align_main: CENTER, flex_align_cross: CENTER, pad_row: 14 }}\n'
        f'                      widgets:\n'
        f'{rows}'
    )


def render_sensors_header_fragment(page: dict, page_index: int) -> str:
    """Baut die text_sensor:-Eintraege (ein Eintrag pro Entity), die eine
    generische Sensor-Seite mit HA-Werten fuettern - werden von generate()
    in die bestehende text_sensor:-Sektion des Headers eingefuegt."""
    entities = page.get("entities") or []
    parts = []
    for i, ent in enumerate(entities):
        entity_id = ent.get("entity_id", "")
        unit = ent.get("unit") or ""
        suffix = f" {_yaml_dq(unit)}" if unit else ""
        parts.append(
            f'  ### Seitenplan-generiert: "{_yaml_dq(page.get("title") or "")}"\n'
            f'  - platform: homeassistant\n'
            f'    id: sensorseite_{page_index}_wert_{i}\n'
            f'    entity_id: "{_yaml_dq(entity_id)}"\n'
            f'    on_value:\n'
            f'      - lvgl.label.update:\n'
            f'          id: lbl_sensorseite_{page_index}_{i}\n'
            f'          text: !lambda |-\n'
            f'            return x + "{suffix}";\n'
        )
    return "".join(parts)


def _insert_into_section(text: str, section_name: str, new_items: str) -> str:
    """Fuegt new_items (fertig formatierte YAML-Listen-Elemente, 2 Leerzeichen
    eingerueckt) am Ende der Top-Level-Sektion 'section_name:' ein (z.B.
    'text_sensor:'). Die Sektion muss bereits existieren."""
    if not new_items:
        return text
    lines = text.splitlines(keepends=True)
    section_re = re.compile(rf"^{re.escape(section_name)}:\s*$")
    idx = next((i for i, line in enumerate(lines) if section_re.match(line)), None)
    if idx is None:
        raise ParseError(f"Sektion {section_name!r} nicht gefunden - kann sensors-Seite nicht einfuegen")
    end = _find_block_end(lines, idx, 0)
    return "".join(lines[:end]) + new_items + "".join(lines[end:])


# Erkennt YAML-Schluessel "id: xxx" (Definition) und C++-Lambda-Referenzen
# "id(xxx)" - beides IDs, die bei einer Mehrfach-Instanz umbenannt werden
# muessen, damit zwei Kopien desselben Blocks (z.B. zwei Klimaanlagen-
# Seiten) nicht auf dieselben Widgets/Sensoren zeigen.
_ID_DEF_RE = re.compile(r"\bid:\s*(\w+)")
_ID_REF_RE = re.compile(r"\bid\((\w+)\)")


def _collect_ids(text: str) -> set[str]:
    return set(_ID_DEF_RE.findall(text)) | set(_ID_REF_RE.findall(text))


def _suffix_ids(text: str, ids: set[str], suffix: str) -> str:
    """Haengt suffix an jedes Vorkommen jeder ID in ids an (Wortgrenzen,
    laengste IDs zuerst ersetzt, um Teilstring-Ueberschneidungen bei
    aehnlich benannten IDs zu vermeiden)."""
    for old_id in sorted(ids, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(old_id)}\b", old_id + suffix, text)
    return text


def _remap_entity_ids(text: str, page_type: str, instance: str) -> str:
    """Ersetzt die Legacy-Entity-ID-Strings (light.fridolin_licht_N /
    climate.fridolin_heizung) durch die instanz-parametrisierte Variante
    - muss exakt zu den Helpern light_entity_id()/climate_entity_id() in
    custom_components/fridolin_display/const.py passen."""
    if page_type == "light":
        return re.sub(
            r"light\.fridolin_licht_(\d+)\b",
            rf"light.fridolin_licht_{instance}_\1",
            text,
        )
    if page_type == "climate":
        return text.replace("climate.fridolin_heizung", f"climate.fridolin_climate_{instance}")
    return text


def render_extra_instance(
    page_type: str, instance: str, original_header_lines: list[str], tile_block: str
) -> tuple[str, dict[str, str]]:
    """Baut eine instanz-suffixierte Kopie eines Licht-/Klimaanlagen-
    Blocks fuer eine ZUSAETZLICHE (nicht-Legacy) Instanz: alle internen
    Widget-/Sensor-IDs bekommen "__inst<instance>" angehaengt, die
    Legacy-Entity-ID-Strings werden auf die Instanz umgemappt. Gibt
    (neuer_tile_block, {sektion: einzufuegender_text}) zurueck - die
    Fragmente muessen von generate() noch in ihre jeweilige Sektion
    (text_sensor:/sensor:/script:) eingefuegt werden."""
    fragment_specs = MULTI_INSTANCE_SECTIONS.get(page_type)
    if not fragment_specs:
        raise ParseError(
            f"Mehrfach-Instanzen fuer Seitentyp {page_type!r} werden vom "
            "Generator noch nicht unterstuetzt (siehe MULTI_INSTANCE_SECTIONS)."
        )

    by_section: dict[str, list[str]] = {}
    for anchor_re, item_indent, section in fragment_specs:
        matches = [i for i, line in enumerate(original_header_lines) if anchor_re.match(line)]
        if len(matches) != 1:
            raise ParseError(
                f"Anker {anchor_re.pattern!r} fuer Mehrfach-Instanz von "
                f"{page_type!r} ist nicht eindeutig ({len(matches)} Treffer)."
            )
        start, end = _find_item_bounds(original_header_lines, matches[0], item_indent)
        by_section.setdefault(section, []).append("".join(original_header_lines[start:end]))

    suffix = f"__inst{instance}"
    ids = _collect_ids(tile_block + "".join("".join(v) for v in by_section.values()))

    new_tile = _remap_entity_ids(_suffix_ids(tile_block, ids, suffix), page_type, instance)
    new_sections = {
        section: _remap_entity_ids(_suffix_ids("".join(texts), ids, suffix), page_type, instance)
        for section, texts in by_section.items()
    }
    return new_tile, new_sections


def _find_item_bounds(lines: list[str], anchor_idx: int, item_indent: int = ITEM_INDENT) -> tuple[int, int]:
    """Start/Ende (Zeilenindizes, [start, end)) des "- "-Listen-Elements
    (bei Einrueckung item_indent), das die Zeile bei anchor_idx enthaelt."""
    item_re = re.compile(rf"^ {{{item_indent}}}- ")
    comment_re = re.compile(rf"^ {{{item_indent}}}###")

    start = None
    for i in range(anchor_idx, -1, -1):
        if item_re.match(lines[i]):
            start = i
            break
    if start is None:
        raise ParseError(f"Kein Element-Start vor Zeile {anchor_idx + 1} gefunden")

    j = start - 1
    while j >= 0 and comment_re.match(lines[j]):
        start = j
        j -= 1

    end = _find_block_end(lines, anchor_idx, item_indent)
    return start, end


def _find_block_end(lines: list[str], from_idx: int, indent: int) -> int:
    """Naechste Zeile nach from_idx, die (nicht-leer) hoechstens so tief
    eingerueckt ist wie indent - das Ende eines bei from_idx beginnenden
    bzw. es enthaltenden Blocks."""
    for i in range(from_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() == "":
            continue
        line_indent = len(line) - len(line.lstrip(" "))
        if line_indent <= indent:
            return i
    return len(lines)


def _find_key_block_bounds(lines: list[str], key_idx: int, indent: int) -> tuple[int, int]:
    """Start/Ende eines bloss durch 'key:' (kein '- ') eingeleiteten
    Blocks, z.B. 'on_boot:' mit verschachteltem 'priority:'/'then:'."""
    comment_re = re.compile(rf"^ {{{indent}}}###")
    start = key_idx
    j = start - 1
    while j >= 0 and comment_re.match(lines[j]):
        start = j
        j -= 1
    end = _find_block_end(lines, key_idx, indent)
    return start, end


def _find_subkey_bounds(lines: list[str], item_start: int, item_end: int, subkey: str) -> tuple[int, int]:
    """Start/Ende eines verschachtelten Schluessels (z.B. 'on_value:')
    innerhalb eines per _find_item_bounds gefundenen Elements."""
    key_re = re.compile(rf"^(\s*){re.escape(subkey)}:\s*$")
    for i in range(item_start, item_end):
        m = key_re.match(lines[i])
        if not m:
            continue
        key_indent = len(m.group(1))
        end = item_end
        for j in range(i + 1, item_end):
            line = lines[j]
            if line.strip() == "":
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent <= key_indent:
                end = j
                break
        return i, end
    raise ParseError(f"Schluessel {subkey!r} nicht im Element gefunden (Zeilen {item_start + 1}-{item_end})")


_BARE_TOP_LEVEL_KEY_RE = re.compile(r"^(\w+):\s*$")


def _maybe_absorb_empty_parent_key(lines: list[str], start: int, end: int) -> tuple[int, int]:
    """Wenn das entfernte Element das EINZIGE Kind einer eigenen Top-Level-
    Sektion ist (z.B. "tuya_ble_node:\\n  - id: kuehlbox\\n    ..."), auch
    die jetzt leere Sektions-Kopfzeile mit entfernen - eine Sektion ohne
    jedes Element ist bei manchen ESPHome-Komponenten ungueltig (leeres
    Dict statt leerer Liste)."""
    if start == 0 or not _BARE_TOP_LEVEL_KEY_RE.match(lines[start - 1]):
        return start, end
    # Steht nach dem entfernten Element sofort wieder eine Zeile ohne
    # Einrueckung (naechste Sektion/Datei-Ende), war dies das einzige Kind.
    if end >= len(lines) or (lines[end].strip() and not lines[end].startswith(" ")):
        return start - 1, end
    return start, end


def strip_page_fragments(header: str, footer: str, missing_types: set[str]) -> tuple[str, str]:
    """Entfernt die verstreuten Sensor-/Script-/Widget-Fragmente aller
    Seitentypen, die NICHT im Seitenplan vorkommen, aus Header UND Footer -
    sonst referenzieren sie nach dem Entfernen des zugehoerigen tile_*-
    Blocks nicht mehr existierende Widget-IDs (Compile-Fehler). Jeder
    Anker muss ueber Header+Footer zusammen GENAU EINMAL vorkommen (ein
    Seitentyp kann Fragmente in beiden haben, z.B. leveling: Header fuer
    das Wohnmobil-Bild/Script, Footer fuer die Umschalt-Buttons)."""
    sides = {
        "header": header.splitlines(keepends=True),
        "footer": footer.splitlines(keepends=True),
    }
    spans: dict[str, list[tuple[int, int]]] = {"header": [], "footer": []}

    def _locate(anchor_re: re.Pattern, page_type: str) -> tuple[str, int]:
        hits = [
            (side, i)
            for side, lines in sides.items()
            for i, line in enumerate(lines)
            if anchor_re.match(line)
        ]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise ParseError(
                f"Anker {anchor_re.pattern!r} fuer Seitentyp {page_type!r} nicht "
                "gefunden (weder im Header noch im Footer) - wurde "
                "wohnwagen-display.yaml so veraendert, dass die "
                "*_ANCHORS-Zuordnungen nicht mehr stimmen?"
            )
        raise ParseError(
            f"Anker {anchor_re.pattern!r} fuer Seitentyp {page_type!r} ist mehrdeutig "
            f"({len(hits)} Treffer: {hits}) - Anker muss eindeutig sein, sonst wird "
            "versehentlich das falsche Element entfernt."
        )

    for page_type in missing_types:
        for anchor_re, item_indent in REMOVE_ITEM_ANCHORS.get(page_type, []):
            side, idx = _locate(anchor_re, page_type)
            lines = sides[side]
            item_start, item_end = _find_item_bounds(lines, idx, item_indent)
            spans[side].append(_maybe_absorb_empty_parent_key(lines, item_start, item_end))

        for anchor_re, subkey, item_indent in STRIP_SUBKEY_ANCHORS.get(page_type, []):
            side, idx = _locate(anchor_re, page_type)
            lines = sides[side]
            item_start, item_end = _find_item_bounds(lines, idx, item_indent)
            spans[side].append(_find_subkey_bounds(lines, item_start, item_end, subkey))

        for anchor_re, key_indent in REMOVE_KEY_BLOCK_ANCHORS.get(page_type, []):
            side, idx = _locate(anchor_re, page_type)
            spans[side].append(_find_key_block_bounds(sides[side], idx, key_indent))

    def _apply(side: str) -> str:
        lines = sides[side]
        side_spans = sorted(spans[side])
        for a, b in zip(side_spans, side_spans[1:]):
            if a[1] > b[0]:
                raise ParseError(f"Ueberlappende Fragmente beim Entfernen ({side}): {a} und {b}")
        keep = []
        cursor = 0
        for start, end in side_spans:
            keep.append("".join(lines[cursor:start]))
            cursor = end
        keep.append("".join(lines[cursor:]))
        return "".join(keep)

    return _apply("header"), _apply("footer")


def generate(plan: list[dict], source_text: str | None = None) -> str:
    """Baut die komplette YAML-Datei aus Seitenplan + Block-Bibliothek."""
    source_text = source_text if source_text is not None else SOURCE_FILE.read_text()
    header, blocks, footer = split_source(source_text)

    plan_types = {page["type"] for page in plan}
    missing_required = REQUIRED_PAGE_TYPES - plan_types
    if missing_required:
        raise ParseError(
            f"Seitentyp(en) {sorted(missing_required)} muessen immer im Plan "
            "enthalten sein (verstreute Abhaengigkeiten noch nicht erfasst, "
            "siehe CLAUDE.md 'Seitenplan / Seiten-Baukasten')."
        )
    missing_types = (
        set(blocks) - plan_types
    )
    known_removable = set(REMOVE_ITEM_ANCHORS) | set(STRIP_SUBKEY_ANCHORS) | set(REMOVE_KEY_BLOCK_ANCHORS)
    unsupported_removal = missing_types - known_removable
    if unsupported_removal:
        raise ParseError(
            f"Seitentyp(en) {sorted(unsupported_removal)} fehlen im Plan, aber der "
            "Generator kennt noch keine Aufraeum-Regeln dafuer (siehe "
            "REMOVE_ITEM_ANCHORS/STRIP_SUBKEY_ANCHORS/REMOVE_KEY_BLOCK_ANCHORS) - "
            "Weglassen wuerde vermutlich eine nicht kompilierende Datei erzeugen."
        )
    if missing_types:
        header, footer = strip_page_fragments(header, footer, missing_types)

    # sensors-Seiten werden nicht aus der Block-Bibliothek kopiert,
    # sondern aus ihrer 'entities'-Liste frisch gerendert (siehe
    # render_sensors_tile) - ihre text_sensor:-Eintraege muessen VOR dem
    # Zusammenbau der tiles-Liste in den Header eingefuegt werden.
    for page_index, page in enumerate(plan):
        if page["type"] == "sensors":
            header = _insert_into_section(
                header, "text_sensor", render_sensors_header_fragment(page, page_index)
            )

    # Instanz je light/climate-Seite bestimmen (aus dem Plan uebernehmen,
    # sonst wie page_plan.py automatisch vergeben: erstes Vorkommen eines
    # Typs = LEGACY_INSTANCE, jedes weitere "2", "3", ...) - Mehrfach-
    # Instanzen von light/climate brauchen instanz-suffixierte Kopien
    # ihrer Bloecke/Fragmente, sonst kollidieren ihre Widget-/Sensor-IDs.
    instance_counts: dict[str, int] = {}
    instances: list[str | None] = []
    for page in plan:
        page_type = page["type"]
        if page_type not in MULTI_INSTANCE_SECTIONS:
            instances.append(None)
            continue
        instance_counts[page_type] = instance_counts.get(page_type, 0) + 1
        instance = str(page.get("instance") or "")
        if not instance:
            instance = LEGACY_INSTANCE if instance_counts[page_type] == 1 else str(instance_counts[page_type])
        instances.append(instance)

    # Original-Header VOR jeder Mehrfach-Instanz-Einfuegung einfrieren -
    # die Legacy-Fragmente (instance == "1") bleiben dort unveraendert
    # liegen, jede weitere Instanz wird aus dieser Momentaufnahme extrahiert
    # (die exakten Anker matchen nur die unsuffixierte Legacy-Kopie, siehe
    # render_extra_instance - ein bereits eingefuegtes __instN wuerde also
    # ohnehin nie versehentlich erneut aufgegriffen).
    original_header_lines = header.splitlines(keepends=True)
    tile_overrides: dict[int, str] = {}
    for i, (page, instance) in enumerate(zip(plan, instances)):
        page_type = page["type"]
        if instance is None or instance == LEGACY_INSTANCE:
            continue
        if page_type not in blocks:
            raise ParseError(f"Seitentyp {page_type!r} hat keinen Block fuer Mehrfach-Instanzen")
        new_tile, new_sections = render_extra_instance(
            page_type, instance, original_header_lines, blocks[page_type]
        )
        tile_overrides[i] = new_tile
        for section, text in new_sections.items():
            header = _insert_into_section(header, section, text)

    rendered_tiles = []
    for column, page in enumerate(plan):
        page_type = page["type"]
        if page_type == "sensors":
            rendered_tiles.append(render_sensors_tile(page, column, column))
            continue
        if page_type not in blocks:
            raise ParseError(
                f"Seitentyp {page_type!r} hat (noch) keinen Block in der "
                f"Block-Bibliothek ({sorted(blocks)}) - siehe CLAUDE.md, "
                "'Seitenplan / Seiten-Baukasten': neue Seitentypen brauchen "
                "zuerst ein eigenes Widget-Template."
            )
        block = tile_overrides.get(column, blocks[page_type])
        block = set_column(block, column)
        title = page.get("title")
        if page_type != "overview" and title:
            block = set_title(block, title)
        rendered_tiles.append(block)

    return header + "".join(rendered_tiles) + footer


def _plan_from_source_order(blocks_order: list[str]) -> list[dict]:
    """Baut einen Seitenplan, der die aktuelle Datei-Reihenfolge/-Titel
    widerspiegelt - fuer den --check Round-Trip-Selbsttest."""
    titles = {
        "overview": "Übersicht",
        "light": "Licht",
        "climate": "Klimaanlage",
        "leveling": "Nivellierung",
        "fridge": "Kühlbox",
    }
    return [{"type": t, "title": titles[t]} for t in blocks_order]


def run_check() -> int:
    source_text = SOURCE_FILE.read_text()
    header, blocks, footer = split_source(source_text)

    # Reihenfolge der Bloecke in der Original-Datei ermitteln (nicht die
    # TILE_ID_BY_TYPE-dict-Reihenfolge, die ist in Python zwar auch
    # insertion-ordered, aber wir wollen hier explizit robust gegen
    # zukuenftige Umsortierungen von TILE_ID_BY_TYPE selbst sein).
    tile_start_re = re.compile(rf"^{TILE_INDENT}- id: (tile_\w+)\s*$")
    order = [
        TYPE_BY_TILE_ID[m.group(1)]
        for line in source_text.splitlines()
        if (m := tile_start_re.match(line))
    ]

    plan = _plan_from_source_order(order)
    generated = generate(plan, source_text=source_text)

    if generated == source_text:
        print("OK: generate(plan) reproduziert wohnwagen-display.yaml Byte fuer Byte.")
        return 0

    print("FEHLER: generierte Datei weicht vom Original ab.", file=sys.stderr)
    gen_lines = generated.splitlines()
    src_lines = source_text.splitlines()
    for i, (a, b) in enumerate(zip(src_lines, gen_lines)):
        if a != b:
            print(f"  erste Abweichung bei Zeile {i + 1}:", file=sys.stderr)
            print(f"    original:   {a!r}", file=sys.stderr)
            print(f"    generiert:  {b!r}", file=sys.stderr)
            break
    else:
        print(
            f"  unterschiedliche Laenge: original {len(src_lines)} Zeilen, "
            f"generiert {len(gen_lines)} Zeilen",
            file=sys.stderr,
        )
    return 1


def extract_page_plan(parsed: Any) -> list[dict]:
    """Holt den Seitenplan aus geparstem JSON, gleich in welcher der drei
    Formen es vorliegt:

    1. Die rohe Seitenplan-Liste selbst.
    2. Der Rueckgabewert von diagnostics.py direkt
       (dict mit "page_plan"-Schluessel auf oberster Ebene) - z.B. wenn
       der Diagnose-Endpunkt der HA-REST-API direkt abgefragt wird (siehe
       apply_page_plan_from_ha.py).
    3. Der tatsaechliche Datei-Inhalt von Home Assistants eingebautem
       "Diagnose herunterladen"-Knopf - HA umschliesst dafuer den
       Rueckgabewert von diagnostics.py zusaetzlich mit einem Umschlag
       ("home_assistant"/"custom_components"/"integration_manifest"/
       "data"), der Plan liegt dort also unter "data" -> "page_plan"
       statt auf oberster Ebene.
    """
    if isinstance(parsed, dict):
        if "page_plan" in parsed:
            return parsed["page_plan"]
        data = parsed.get("data")
        if isinstance(data, dict) and "page_plan" in data:
            return data["page_plan"]
    return parsed


def _load_plan(path: Path) -> list[dict]:
    """Laedt den Seitenplan aus einer JSON-Datei - akzeptiert alle drei in
    extract_page_plan() beschriebenen Formen, damit sowohl ein manuell
    heruntergeladener Diagnose-Export als auch die rohe Plan-Liste direkt
    an --plan uebergeben werden koennen."""
    return extract_page_plan(json.loads(path.read_text()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, help="Seitenplan als JSON-Datei")
    parser.add_argument("--out", type=Path, help="Zieldatei (Default: stdout)")
    parser.add_argument(
        "--check", action="store_true", help="Round-Trip-Selbsttest, siehe Modul-Docstring"
    )
    args = parser.parse_args()

    if args.check:
        return run_check()

    if not args.plan:
        parser.error("--plan ist erforderlich (ausser bei --check)")

    plan = _load_plan(args.plan)
    result = generate(plan)

    if args.out:
        args.out.write_text(result)
        print(f"Geschrieben: {args.out}")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
