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
Kommentarzeilen direkt davor) erkannt und als Rohtext extrahiert. Alles
ausserhalb dieser Liste (Hardware, WLAN, Wetter-System, Kuehlbox-BLE,
Nivellierungs-Sensorik, Einstellungen-Overlay, Bild-Assets, ...) bleibt
unveraendert - der Seitenplan steuert bisher NUR, welche der fuenf
Bloecke in welcher Reihenfolge/mit welchem Titel in die tiles:-Liste
kommen, nicht deren Inhalt (siehe CLAUDE.md, "Seitenplan / Seiten-
Baukasten" fuer den Stand/die Grenzen).

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


def generate(plan: list[dict], source_text: str | None = None) -> str:
    """Baut die komplette YAML-Datei aus Seitenplan + Block-Bibliothek."""
    source_text = source_text if source_text is not None else SOURCE_FILE.read_text()
    header, blocks, footer = split_source(source_text)

    rendered_tiles = []
    for column, page in enumerate(plan):
        page_type = page["type"]
        if page_type not in blocks:
            raise ParseError(
                f"Seitentyp {page_type!r} hat (noch) keinen Block in der "
                f"Block-Bibliothek ({sorted(blocks)}) - siehe CLAUDE.md, "
                "'Seitenplan / Seiten-Baukasten': neue Seitentypen (z.B. "
                "'sensors') brauchen zuerst ein eigenes Widget-Template."
            )
        block = blocks[page_type]
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
        "fridge": "Kuehlbox",
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

    plan = json.loads(args.plan.read_text())
    result = generate(plan)

    if args.out:
        args.out.write_text(result)
        print(f"Geschrieben: {args.out}")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
