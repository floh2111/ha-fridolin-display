#!/usr/bin/env python3
"""Zieht den aktuellen Seitenplan direkt per Home-Assistant-REST-API und
generiert daraus in einem Rutsch eine neue wohnwagen-display.yaml -
erspart den manuellen Weg "Diagnose herunterladen" -> Datei speichern ->
generate_display_yaml.py --plan von Hand aufrufen.

Voraussetzung: ein Long-Lived Access Token mit Admin-Rechten (Home
Assistant -> Profil -> Sicherheit -> "Langlebige Zugangs-Token" ->
"Token erstellen"). Admin-Rechte sind noetig, weil sowohl der
Config-Entries- als auch der Diagnose-Endpunkt das voraussetzen.

Nutzung:
    export HA_URL=https://deine-ha-instanz:8123
    export HA_TOKEN=eyJ...
    python3 esphome/apply_page_plan_from_ha.py --out esphome/wohnwagen-display.yaml

Die Fridolin-Display-Config-Entry wird automatisch gefunden (die
Integration laesst ohnehin nur eine einzige Instanz zu, siehe
async_set_unique_id(DOMAIN) in config_flow.py) - keine Entry-ID von
Hand heraussuchen noetig. Bei Bedarf laesst sie sich trotzdem manuell
vorgeben (--entry-id), z.B. falls die Auto-Suche aus irgendeinem Grund
mehrdeutig sein sollte.

Ohne --out wird das Ergebnis auf stdout geschrieben (wie bei
generate_display_yaml.py). Mit --save-plan wird der abgerufene
Seitenplan zusaetzlich als eigene JSON-Datei gespeichert, z.B. zur
Kontrolle oder um ihn spaeter offline erneut an generate_display_yaml.py
--plan uebergeben zu koennen.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import generate_display_yaml as gen

DOMAIN = "fridolin_display"


class HaApiError(SystemExit):
    """Fehler beim Zugriff auf die Home-Assistant-REST-API - SystemExit-
    Unterklasse, damit main() sie einfach durchreichen kann und die
    Fehlermeldung statt eines Tracebacks auf der Konsole landet."""


def _api_get(base_url: str, token: str, path: str) -> Any:
    url = base_url.rstrip("/") + path
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")[:500]
        raise HaApiError(
            f"HA-API-Fehler {err.code} bei {path}: {body}"
        ) from err
    except urllib.error.URLError as err:
        raise HaApiError(f"HA unter {base_url!r} nicht erreichbar: {err}") from err


def _find_entry_id(base_url: str, token: str) -> str:
    """Findet die (einzige) Config Entry der Fridolin-Display-Integration
    automatisch ueber den Config-Entries-Endpunkt."""
    entries = _api_get(base_url, token, "/api/config/config_entries/entry")
    matches = [e for e in entries if e.get("domain") == DOMAIN]
    if not matches:
        raise HaApiError(
            f"Keine Config Entry fuer Domain {DOMAIN!r} gefunden - ist die "
            "Integration in Home Assistant eingerichtet?"
        )
    if len(matches) > 1:
        # Sollte wegen async_set_unique_id(DOMAIN) eigentlich nie vorkommen.
        ids = ", ".join(e["entry_id"] for e in matches)
        raise HaApiError(
            f"Mehrere Config Entries fuer {DOMAIN!r} gefunden ({ids}) - "
            "das ist unerwartet, bitte die gewuenschte mit --entry-id angeben."
        )
    return matches[0]["entry_id"]


def fetch_page_plan(base_url: str, token: str, entry_id: str | None) -> list[dict]:
    entry_id = entry_id or _find_entry_id(base_url, token)
    diagnostics = _api_get(
        base_url, token, f"/api/diagnostics/config_entry/{entry_id}"
    )
    plan = gen.extract_page_plan(diagnostics)
    if not isinstance(plan, list):
        raise HaApiError(
            "Kein Seitenplan im Diagnose-Export gefunden - unerwartetes "
            "Antwortformat der HA-API."
        )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--ha-url",
        default=os.environ.get("HA_URL"),
        help="z.B. https://deine-ha-instanz:8123 (Default: Umgebungsvariable HA_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("HA_TOKEN"),
        help="Long-Lived Access Token (Default: Umgebungsvariable HA_TOKEN)",
    )
    parser.add_argument(
        "--entry-id",
        default=None,
        help="Config-Entry-ID ueberspringt die automatische Suche",
    )
    parser.add_argument("--out", type=Path, help="Zieldatei (Default: stdout)")
    parser.add_argument(
        "--save-plan",
        type=Path,
        help="Abgerufenen Seitenplan zusaetzlich als JSON-Datei speichern",
    )
    args = parser.parse_args()

    if not args.ha_url or not args.token:
        parser.error(
            "--ha-url/--token (oder die Umgebungsvariablen HA_URL/HA_TOKEN) "
            "sind erforderlich."
        )

    plan = fetch_page_plan(args.ha_url, args.token, args.entry_id)

    if args.save_plan:
        args.save_plan.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        )
        print(f"Seitenplan gespeichert: {args.save_plan}", file=sys.stderr)

    result = gen.generate(plan)

    if args.out:
        args.out.write_text(result)
        print(f"Geschrieben: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
