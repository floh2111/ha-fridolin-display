# Übergabe: Fridolin Display

Diese Datei ist die Übergabe an eine neue (z.B. lokale) Claude-Code-Sitzung,
damit sie ohne weitere Rückfragen dort weitermachen kann, wo diese Session
aufgehört hat. Sie fasst Projektziel, Architektur, aktuellen Stand und
offene Punkte zusammen. Wenn du (Claude) diese Datei liest: der Nutzer
heißt Florian (GitHub: floh2111), spricht Deutsch, und du kannst direkt
weiterarbeiten, ohne das Projekt neu zu erklären.

## Projektziel

Florian hat einen Wohnwagen namens **"Fridolin"**. Er baut eine
Touch-Bedienoberfläche dafür auf Basis des **Waveshare
ESP32-S3-Touch-LCD-7** (800×480, GT911-Touch, ESP32-S3, 8 MB PSRAM,
16 MB Flash, IO-Expander CH422G), mit **ESPHome + LVGL** (ESPHome 2026.9).
Zwischenzeitlich stand ein Umstieg auf das größere 7B-Board (1024×600) im
Raum und wurde auch umgesetzt, Florian hat sich aber wieder für das
kleinere 800×480-Board entschieden – die aktuelle `wohnwagen-display.yaml`
ist wieder komplett auf 800×480 zurückgebaut (siehe Git-Historie für die
7B-Variante, falls doch nochmal gebraucht). Das Display hängt am
Wohnwagen, der Wohnwagen ist per VPN-Router mit Florians Heimnetz und
seiner **Home Assistant**-Instanz verbunden.

Nur der Neigungssensor (**GY-521 / MPU6050**) ist physisch direkt am
ESP32 verbaut. Die Kühlbox (Euhomy Car Fridge CF, Tuya-BLE) wird ebenfalls
**direkt vom ESP** per Bluetooth angesprochen (nicht über Home Assistant).
Alle anderen Entitäten (Lichter, Klimaanlage) sind echte, bereits
existierende Home-Assistant-Entitäten – das Display steuert sie nur fern.

## Architektur (wichtig!)

Damit sich alles, was auf dem Display angezeigt wird (welches Licht,
welche Klimaanlage, welcher Standort-Tracker), **über die Home-Assistant-UI
konfigurieren lässt statt hart in der ESPHome-YAML verdrahtet zu sein**,
gibt es eine **selbstgeschriebene Home-Assistant-Custom-Integration**
(`custom_components/fridolin_display/`). Sie funktioniert als
Proxy-/Spiegel-Schicht:

- Der ESP32 spricht **immer nur mit einer festen Handvoll Entities**
  dieser Integration (`light.fridolin_licht_1` … `_4`,
  `climate.fridolin_heizung`, `sensor.fridolin_wetter_*`,
  `sensor.fridolin_standort_status`, `button.fridolin_standort_uebernehmen`).
- Über die **Options-Seite der Integration** in Home Assistant stellt
  Florian ein, welche **echten** Licht-/Klimaanlagen-Entities dahinterstecken.
  Das wirkt sofort, ohne den ESP32 neu zu flashen.
- Ein eigener `DataUpdateCoordinator` holt Wetterdaten (aktuell +
  Stundenvorhersage + morgen) direkt von **OpenWeatherMap**, Standort
  kommt von einem `device_tracker` (Home-Assistant-App) oder wird über
  einen Button ("Standort übernehmen") manuell fixiert.
- Die Dashboard-Karte für die Nivellierung ist **seit Integrations-
  Version 0.2.0 kein Teil dieser Integration mehr**, sondern ein
  eigenständiges Repo: **[floh2111/rv-leveling-card](https://github.com/floh2111/rv-leveling-card)**
  (eigenes HACS-Dashboard-Repository, Kategorie "plugin"/Dashboard).
  Grund: nur so taucht sie in HACS als eigenständige Lovelace-Karte auf,
  unabhängig installierbar von der Integration. Zeigt die Nivellierung
  im selben Stil wie das Display, mit der Front nach oben statt nach
  rechts. Im Karteneditor wählbar: Wohnwagen (Deichsel) oder Wohnmobil
  (Frontscheibe) – eigenes `VEHICLE_ART`-Objekt mit eigenem
  SVG/viewBox/Röhren-Geometrie je Typ, per `ha-form`-Editor
  (`vehicle_type`) umschaltbar, inkl. visuellem UI-Karteneditor für
  Titel + alle Entity-IDs. Der Custom-Element-Typ heißt seit
  `rv-leveling-card` Version 2.0.0 `rv-leveling-card` (vorher
  `fridolin-nivellierung-card` - auf Florians Wunsch umbenannt, er
  konfiguriert sein Dashboard einmalig neu).

Genaue Entity-ID-Tabelle und Klimaanlagen-Details stehen in
`custom_components/fridolin_display/README.md`; die Karte hat ihre
eigene README im `rv-leveling-card`-Repo.

### Seitenplan / Seiten-Baukasten (seit Integrations-Version 0.3.0, WIP)

Florian möchte Reihenfolge, Auswahl und Titel der Display-Seiten flexibel
gestalten können, inkl. Mehrfach-Instanzen (z.B. zwei Klimazonen) und
neuer Seiten-Typen (zuerst: generische Sensor-Seite; Karte mit
Standort-Pins wurde explizit **abgelehnt**, siehe Konversation).
Wichtiger technischer Befund: LVGL-Widgets sind zur **Compile-Zeit**
fest, ein "jeder Slot kann jeden Seitentyp zeigen"-Baukasten zur
Laufzeit würde die Widget-Zahl vervielfachen und den RAM des ESP32-S3
sprengen. Gewählter Ansatz (Ansatz B): **Seitenplan-Editor in der
HA-Integration + YAML-Generator**, der daraus die passende
`wohnwagen-display.yaml` erzeugt – Reihenfolge/Auswahl der Seiten
braucht dadurch einen Reflash, Entity-Zuordnung *innerhalb* einer
bestehenden Seite nicht (wie bisher).

**Bereits umgesetzt** (Python-Seite, `custom_components/fridolin_display/`):
- `const.py`: `CONF_PAGE_PLAN`, `PAGE_TYPE_*`, `DEFAULT_PAGE_PLAN`
  (entspricht 1:1 dem bisherigen 5-Seiten-Display), sowie Helper
  (`climate_target_key`, `light_slot_entity_key`, `climate_entity_id`,
  `light_entity_id`), die zwischen der **Legacy-Instanz** (`"1"`, alte
  Entity-IDs `climate.fridolin_heizung`/`light.fridolin_licht_1.._4`)
  und weiteren, instanz-parametrisierten Instanzen vermitteln.
- `page_plan.py`: liest + normalisiert den Seitenplan aus den Options
  (Fallback auf `DEFAULT_PAGE_PLAN`), vergibt fehlende `instance`-Werte
  automatisch.
- `light.py`/`climate.py`: erzeugen jetzt **eine Entity-Gruppe pro
  Licht-/Klimaanlagen-Seite im Plan** statt einer fest verdrahteten
  Gruppe - mehrere Instanzen funktionieren bereits (nur der YAML-Teil
  fehlt noch, siehe unten).
- `config_flow.py`: Options-Flow jetzt zweistufig - Schritt 1
  (`async_step_init`) editiert den Seitenplan als **JSON-Textfeld**
  (bewusst kein Multi-Step-Wizard mit Hinzufügen/Entfernen/Verschieben -
  das wäre ein eigenes, größeres Stück Arbeit), Schritt 2
  (`async_step_entities`) baut das Entity-Zuordnungsformular dynamisch
  aus dem gerade eingegebenen Plan.
- Rückwärtskompatibel: Ohne eigenen Seitenplan verhält sich alles exakt
  wie vorher (gleiche Entity-IDs), da `DEFAULT_PAGE_PLAN` nur
  Legacy-Instanzen enthält.

**YAML-Generator** (`esphome/generate_display_yaml.py`) – Milestone 1 +
"Seiten weglassen" (inkl. `leveling`) fertig und verifiziert:
- Funktionsweise: `wohnwagen-display.yaml` selbst dient als
  "Block-Bibliothek". Die 5 `tile_*`-Blöcke in der `lvgl: -> pages: ->
  tiles:`-Liste werden anhand der `- id: tile_xxx`-Marker (plus ihrer
  `###`-Kommentarzeilen) per Regex erkannt und als Rohtext extrahiert;
  `generate(plan)` setzt pro Block `column:` (Position im Wisch-
  Karussell) und ersetzt die erste `text: "..."`-Zeile (Titel) -
  Übersicht bleibt unangetastet (hat keine einzelne Titel-Zeile).
- **Seiten weglassen**: `REMOVE_ITEM_ANCHORS`/`STRIP_SUBKEY_ANCHORS`/
  `REMOVE_KEY_BLOCK_ANCHORS` (im Skript) listen für `light`/`climate`/
  `fridge`/`leveling` alle VERSTREUTEN Definitionen (HA-Spiegel-
  `text_sensor`s, Sync-Scripts; bei `fridge` zusätzlich die komplette
  Tuya-BLE-Anbindung; bei `leveling` das Wohnmobil-Bild-Asset, den
  `g_fahrzeugtyp_wohnmobil`-Global, das `sync_fahrzeugtyp`-Script, den
  `on_boot:`-Aufruf - **und die Umschalter-Buttons im FOOTER**
  (Einstellungen-Overlay)) - fehlt einer dieser Typen im Plan, werden
  seine Fragmente per Regex-Anker + automatischer Element-
  Grenzenerkennung (`_find_item_bounds`/`_find_key_block_bounds` für
  bloße `key:`-Blöcke wie `on_boot:` ohne `- `) aus Header UND Footer
  entfernt (`strip_page_fragments(header, footer, missing_types)`),
  inkl. Spezialfall "jetzt leerer Elternschlüssel" (leeres
  `tuya_ble_node:` ohne Kinder ist ungültig, wird mit entfernt). Jeder
  Anker muss über Header+Footer zusammen GENAU EINMAL matchen
  (`_locate`), sonst bricht der Generator kontrolliert ab, statt
  versehentlich das falsche Element zu löschen (ist beim Bauen mehrfach
  tatsächlich passiert, siehe Git-Historie/Commits - u.a. `id: kb_ziel`
  matchte anfangs auch eine verschachtelte Referenz derselben ID in
  einem anderen Element).
- Nur `overview` bleibt Pflicht (`REQUIRED_PAGE_TYPES`) - komplettes
  Wettersystem, Uhrzeit, Standort als viele, wenig klar abgrenzbare
  Abhängigkeiten, außerdem die "Startseite".
- **Verifiziert** (alle mit echtem `esphome compile`, nicht nur
  `config`):
  - `--check`-Selbsttest (Byte-für-Byte-Reproduktion) - läuft in CI.
  - Reihenfolge ändern + Umbenennen (alle 5 Seiten) - kompiliert,
    RAM/Flash identisch zum Original.
  - **Kühlbox weglassen** - kompiliert, RAM/Flash sogar kleiner
    (46,2 % / 35,2 % statt 46,7 % / 35,4 %).
  - **Nivellierung weglassen** (Header + Footer gemeinsam betroffen) -
    kompiliert, RAM/Flash noch kleiner (46,5 % / 30,3 %, v.a. weniger
    Flash durch die wegfallenden Bild-Assets).
  - **Kombiniert weglassen** (Nivellierung + Kühlbox gleichzeitig, nur
    Übersicht/Licht/Klimaanlage übrig) - besteht `esphome config`.
  - Licht/Klimaanlage einzeln weglassen - bestehen `esphome config`.
- **Mehrfach-Instanzen (2. Klimaanlage, 2. Licht-Seite) im Generator:
  fertig und verifiziert.** `render_extra_instance()` extrahiert für die
  ERSTE (Legacy-)Instanz eines Typs nichts Neues (bleibt exakt wie
  bisher, Byte-für-Byte-Test bleibt gültig) - für jede WEITERE Instanz:
  sammelt alle `id:`-Definitionen und `id(...)`-Lambda-Referenzen
  innerhalb des `tile_*`-Blocks + seiner verstreuten Header-Fragmente
  (`_collect_ids`), hängt an JEDE davon `__inst<instance>` an
  (`_suffix_ids`, längste IDs zuerst wegen möglicher Teilstring-
  Überschneidungen), und mappt die Legacy-Entity-ID-Strings
  (`light.fridolin_licht_N`/`climate.fridolin_heizung`) auf die
  instanz-parametrisierte Variante (`_remap_entity_ids` - muss exakt zu
  `light_entity_id()`/`climate_entity_id()` in `const.py` passen).
  `MULTI_INSTANCE_SECTIONS` ordnet jedem Fragment seine Ziel-Sektion zu
  (`text_sensor:`/`sensor:`/`script:` - climate ist auf alle drei
  verteilt), die duplizierten Fragmente werden über das schon für
  `sensors` gebaute `_insert_into_section()` eingefügt.
  - **Verifiziert mit echtem `esphome compile`**: Plan mit 2 Klimaanlagen-
    Seiten kompiliert (RAM/Flash minimal höher, 47,0 % / 35,5 % statt
    46,7 % / 35,4 %), ebenso 2 Licht-Seiten (46,9 % / 35,4 %). Keine
    ID-Kollisionen (`esphome config` hätte sie sofort gemeldet).
- `esphome/page_plan.example.json` reproduziert nachweislich exakt das
  aktuelle Display (Standardtitel, Original-Reihenfolge).
- Nutzung aktuell manuell: Seitenplan (aus dem Options-Flow-JSON-Feld
  oder von Hand) in eine `.json`-Datei speichern, dann
  `python3 esphome/generate_display_yaml.py --plan plan.json --out
  esphome/wohnwagen-display.yaml` und neu flashen. Kein Automatismus
  (Download-Button in der Integration o.ä.) bisher vorhanden.

**Neuer Seitentyp `sensors`** (generische Sensor-Anzeige) - fertig und
verifiziert, funktioniert grundlegend ANDERS als die 5 Bestandsseiten:
- Kein fester Block in der Block-Bibliothek (kann es auch nicht geben -
  beliebig viele/wählbare Entities pro Seite). Stattdessen rendert
  `render_sensors_tile(page, column, page_index)` den `tile_*`-Block bei
  jedem Aufruf frisch aus der `entities`-Liste des Plan-Eintrags: pro
  Entity eine Zeile (Label + Wert) in einer vertikalen Flex-Liste, ohne
  Entities ein Platzhaltertext "Keine Sensoren eingerichtet".
- `render_sensors_header_fragment(page, page_index)` baut dazu passende
  `text_sensor: platform: homeassistant`-Einträge (ein Sensor pro
  Entity, `on_value` aktualisiert das Wert-Label) - referenziert die in
  der `entities`-Liste angegebenen **echten HA-Entity-IDs direkt**, ganz
  ohne Mirror-Entity über die Integration (anders als light/climate):
  da eine Änderung der Seite ohnehin einen Reflash braucht, lohnt die
  Indirektion hier nicht. `_insert_into_section(header, "text_sensor",
  fragment)` fügt das Fragment in die bestehende `text_sensor:`-Sektion
  ein (neue, generische Hilfsfunktion, nicht auf sensors beschränkt).
- Plan-Eintrag-Format: `{"type": "sensors", "title": "...", "entities":
  [{"entity_id": "sensor.x", "label": "...", "unit": "..."}]}` -
  `entities` akzeptiert auch bloße Entity-ID-Strings (Label = Entity-ID,
  kein Unit-Suffix). `page_plan.py`s `_normalize_sensor_entities`
  normalisiert beides einheitlich (Python/HA-Seite bisher rein
  strukturell - keine eigenen Mirror-Entities für sensors, siehe oben).
- Widget-/Sensor-IDs werden mit dem Plan-Index der Seite suffixiert
  (`tile_sensorseite_<i>`, `lbl_sensorseite_<i>_<j>`), eindeutig auch
  bei mehreren sensors-Seiten im selben Plan.
- **Verifiziert mit echtem `esphome compile`**: Plan mit einer
  3-Zeilen-sensors-Seite (Batterie/Frischwasser/Abwasser, %) neben den
  5 Bestandsseiten kompiliert, RAM/Flash praktisch identisch zum
  Original (46,8 % / 35,4 %). Zwei sensors-Seiten gleichzeitig (eine
  davon mit leerer `entities`-Liste) bestehen `esphome config`, IDs
  bleiben eindeutig.
- Ein Bug beim Bauen gefunden+behoben: `pad_left`/`pad_right` gehören
  bei ESPHome-LVGL NICHT in den `layout:`-Block (dort nur
  `pad_row`/`pad_column` für Flex-Abstände), sondern als eigene
  Widget-Eigenschaften auf das `obj:` selbst.

**Export-Knopf + Menü-Editor** (seit Integrations-Version 0.4.0) -
fertig, mit Stub-Home-Assistant-Modulen (siehe unten) end-to-end
durchgetestet, aber **noch nicht in einer echten HA-Instanz gesehen**:
- `diagnostics.py`: nutzt HAs eingebauten "Diagnose herunterladen"-
  Knopf (Einstellungen → Geräte & Dienste → Fridolin Display → ⋮) -
  kein eigenes UI nötig. Liefert u.a. den aktuellen Seitenplan unter dem
  Schlüssel `page_plan`, redigiert `owm_api_key`/den Standort-Tracker.
  `generate_display_yaml.py`s `--plan`-Lader (`_load_plan`) erkennt
  diesen Dump automatisch (Dict mit `page_plan`-Schlüssel) UND die rohe
  Plan-Liste - der heruntergeladene Diagnose-Export lässt sich also ohne
  manuelles Herauskopieren direkt an `--plan` übergeben.
- `config_flow.py`: `async_step_init` ist jetzt ein **Menü**
  (`async_show_menu`) statt direkt das JSON-Feld zu zeigen: "Seiten
  verwalten" (neuer Menü-Editor), "Seitenplan als JSON bearbeiten"
  (der bisherige Weg, bleibt als Experten-Fallback für Massenänderungen),
  "Entity-Zuordnung + Speichern" (bestehender Schritt, jetzt Endpunkt
  jedes Pfads). "Seiten verwalten" ist selbst ein Menü mit "Seite
  hinzufügen"/"entfernen"/"verschieben" (jeweils ein eigener
  `async_show_form`-Schritt, der danach zum Menü zurückkehrt) - der
  Plan liegt waehrend der ganzen Options-Flow-Sitzung in
  `self._working_plan` (`page_plan.py`s neue, öffentliche
  `normalize_page_plan()` wird nach jeder Änderung erneut angewendet,
  damit z.B. eine frisch hinzugefügte Licht-/Klimaanlagen-Seite eine
  `instance` bekommt). Eine `sensors`-Seite wählt ihre Entities beim
  Hinzufügen über einen normalen `selector.EntitySelector(multiple=True)`
  aus (kein Eintippen von `entity_id|Label|Einheit` mehr, wie ursprünglich
  gebaut - auf Florians Wunsch durch einen echten Entity-Picker ersetzt,
  analog zum Hinzufügen von Entities in einer Lovelace-Karte). Label/Einheit
  werden dabei automatisch aus `hass.states.get(entity_id)` gelesen
  (`_sensors_entities_from_selection`: Label = `state.name`, i.d.R. der
  friendly_name; Einheit = `unit_of_measurement`-Attribut; ohne State
  bleibt die Entity-ID selbst als Label) - eine Momentaufnahme zum
  Auswahlzeitpunkt, kein Live-Sync. Ein individuell abweichendes Label
  lässt sich weiterhin nur über "Seitenplan als JSON bearbeiten" setzen.
- **Getestet ohne echtes Home Assistant**: `homeassistant`/`voluptuous`
  sind in dieser Umgebung nicht installiert - stattdessen minimale
  Stub-Module (`ConfigEntry`/`ConfigFlow`/`OptionsFlow` mit
  `async_show_menu`/`async_show_form`/`async_create_entry` als reine
  Dict-Rückgaben, `selector.*` als einfache Werte-Container) und ein
  Skript, das den kompletten Flow durchspielt (init → manage_pages →
  zwei add_page-Aufrufe → move_page → remove_page → entities) und den
  `self._working_plan`-Zustand nach jedem Schritt prüft - alle
  Mutationen (Hinzufügen inkl. automatischer Instanz-Vergabe,
  Verschieben, Entfernen) verhalten sich wie erwartet.
  `_sensors_entities_from_selection` zusätzlich isoliert mit einem
  Fake-`hass.states`-Objekt getestet (Label/Einheit-Übernahme, Fallback
  auf Entity-ID ohne State) - alle Assertions grün. Ersetzt keinen echten
  Test in einer laufenden Home-Assistant-Instanz (Übersetzungen/
  `async_show_menu`-Verhalten/Formular-Rendering/echtes
  Entity-Picker-UI ungeprüft).

**Noch offen**:
1. Mehrfach-Instanzen für `fridge` (2. Kühlbox) - bisher nicht in
   `MULTI_INSTANCE_SECTIONS`, da nur eine Kühlbox am Wohnwagen hängt;
   technisch analog zu light/climate nachrüstbar, falls je gebraucht.
2. **Explizit nicht gewünscht**: Kartenansicht mit dauerhaft
   gespeicherten Standort-Pins (Florian hat das abgelehnt) und eine
   separate "Heizung"-Seite (ist inhaltlich dasselbe wie eine zweite
   Klimaanlagen-Seite, kein eigener Typ nötig).

## Repo-Struktur

```
esphome/wohnwagen-display.yaml       – volle Display-Konfiguration (5 Wisch-Seiten + Einstellungs-Overlay), 800x480
esphome/secrets.yaml.example         – Vorlage für WLAN/API-Key (echte secrets.yaml ist gitignored)
esphome/test-esp32-ohne-display.yaml – Testkonfig ohne Display: GY-521 + HA-API-Check + Kühlbox direkt per Tuya-BLE, alles in einer Firmware
esphome/fridolin-vorschau.html       – interaktive Browser-Vorschau der UI (auch als Artifact veröffentlicht)
esphome/images/weather/*.svg         – 16 Wetter-Icons (von Florian geliefert), von ESPHome per resvg gerastert
esphome/images/wasserwaage.svg       – Wohnwagen-Grundriss + Kreuzlibelle für die Nivellierungs-Seite
esphome/images/wohnmobil.svg         – Alternative Grafik (Wohnmobil), gleiche Röhren-Koordinaten wie wasserwaage.svg
esphome/images/zahnrad.svg           – selbst gezeichnetes Zahnrad-Icon für den Einstellungen-Knopf (kein Font-Glyph, siehe "Wichtige technische Details")
esphome/generate_display_yaml.py     – Seitenplan-JSON -> wohnwagen-display.yaml (siehe "Seitenplan / Seiten-Baukasten")
esphome/apply_page_plan_from_ha.py   – zieht den Seitenplan direkt per HA-REST-API und ruft generate_display_yaml.py in einem Rutsch auf
custom_components/fridolin_display/  – die Home-Assistant-Integration (ConfigFlow, OptionsFlow, Coordinator, Entities)
.github/workflows/validate.yml       – CI: `esphome config` + echter `esphome compile` beider Configs, hassfest für die Integration
```

Die Lovelace-Karte (`rv-leveling-card.js`) liegt **nicht** in diesem
Repo, sondern in `floh2111/rv-leveling-card` (separat geklont, falls du
daran arbeiten musst).

## UI-Struktur (ESPHome/LVGL)

Fünf Seiten als Wisch-Karussell (LVGL `tileview`) plus eine Einstellungsseite, die NICHT im
Wisch-Karussell hängt, sondern nur über einen kleinen Zahnrad-Button auf
der Übersichtsseite erreichbar ist (LVGL `top_layer:`):

1. **Übersicht** – vier Felder: oben links aktuelles Wetter + Stundenvorhersage
   (4 Slots, mit echten Wetter-Icons), oben rechts Uhrzeit/Datum/Standort +
   Morgen-Ausblick. Unten bewusst frei gelassen (für später). Zahnrad-Button
   oben führt zu "Einstellungen" (eigenes SVG-Icon `img_zahnrad`, kein
   Font-Glyph). Oben links zusätzlich ein Verbindungs-Hinweis
   (`box_verbindung_verloren`, roter Punkt + "Keine Verbindung"), nur
   sichtbar, wenn die API-Verbindung zu Home Assistant unterbrochen ist
   (`api: on_client_connected`/`on_client_disconnected`) - sonst würden
   eingefrorene Wetter-/Licht-/Klimaanlage-Werte kommentarlos als aktuell
   erscheinen.
2. **Licht** – An/Aus-Schalter für bis zu 4 konfigurierte Lichter, unbelegte
   Slots werden ausgeblendet.
3. **Klimaanlage** (`tile_heizung`, Entity weiterhin `climate.fridolin_heizung`)
   – großer Zieltemperatur-Wert in einem zweifarbigen Ring (roter Teil unterhalb
   der aktuellen Ist-Temperatur, blauer Teil oberhalb), −/+, Modus-Knöpfe
   Aus/Heizen/Kühlen, Programm-Knöpfe Eco/Normal/Max (fester `preset_mode`,
   1:1 an die Zielentität durchgereicht). Vom Aufbau wie die Kühlbox-Seite.
4. **Nivellierung** – Fahrzeug-Grundriss (Draufsicht, Front rechts) mit
   einer echten Kreuzlibelle: waagerechte ovale Libelle in Fahrtrichtung
   (Vorne/Hinten), senkrechte im rechten Winkel dazu (Links/Rechts), je mit
   zwei Mittelstrichen statt eines Rings. Werte aus dem GY-521 per `atan2`,
   "Nullen"-Knopf speichert den Nullpunkt lokal im Flash des ESP. Braucht
   keine Internet-/HA-Verbindung, läuft komplett lokal auf dem ESP. Grafik
   umschaltbar zwischen Wohnwagen (`img_wasserwaage`, Deichsel) und
   Wohnmobil (`img_wohnmobil`, Frontscheibe) – Einstellung dazu auf der
   Einstellungsseite (siehe Punkt 6), beide Bilder nutzen exakt dieselben
   Röhren-Koordinaten, daher keine Änderung an der Blasen-Logik nötig.
5. **Kühlbox** – runde Zieltemperatur-Anzeige mit −/+, Ein/Aus, Modus MAX/ECO,
   Batterieschutz L/M/H. Die Kühlbox (Euhomy Car Fridge CF, Tuya-BLE, Kategorie
   `xbx`) wird **direkt vom ESP** per Bluetooth gelesen/gesteuert, ohne Home
   Assistant, über die externe Komponente `floh2111/esphome-tuya-ble-fridolin`
   (Fork von Noneawe/BillyNate, auf einen Commit gepinnt, mit Schreibzugriff
   erweitert). Nur eine BLE-Verbindung zur Kühlbox möglich: Tuya-App und
   HA-Integration "Tuya BLE" müssen aus sein.
6. **Einstellungen (Overlay, nicht wischbar)** – Fahrzeugtyp-Umschalter
   für die Nivellierungs-Seite (Wohnwagen/Wohnmobil, zwei checkbare
   Knöpfe, persistiert in `g_fahrzeugtyp_wohnmobil`, angewendet über
   `sync_fahrzeugtyp` inkl. `on_boot`), Button "Standort
   übernehmen" (nimmt die Koordinaten vom `device_tracker` und setzt sie
   als festen Wetter-Standort), Anzeige des letzten Übernahme-Zeitpunkts,
   "Zurück"-Button.

## Aktueller Stand (Stand: 2026-09-27)

- ✅ ESPHome-Konfiguration fertig geschrieben (`wohnwagen-display.yaml`),
  aktuell wieder auf 800×480 (siehe Projektziel oben).
- ✅ Home-Assistant-Integration fertig geschrieben, inkl. ConfigFlow,
  OptionsFlow, Coordinator, Light/Climate/Sensor/Button-Entities.
- ✅ GitHub-Repo `floh2111/ha-fridolin-display` eingerichtet, Push-Zugriff
  funktioniert.
- ✅ Lovelace-Karte in ein eigenes Repo ausgelagert:
  `floh2111/rv-leveling-card` (öffentlich, MIT-Lizenz, eigene
  `hacs.json`/README/CI mit `hacs/action`). In der Integration dafür
  entfernt: `www/`-Ordner, `_async_register_frontend_static_path` in
  `__init__.py`, `after_dependencies: [http]` in `manifest.json` (nicht
  mehr gebraucht, da kein `hass.http`-Zugriff mehr). **Breaking Change**
  für Alt-Installationen: die alte Ressourcen-URL
  `/fridolin_display/fridolin-nivellierung-card.js` funktioniert nicht
  mehr, einmalig auf die neue Ressource aus `rv-leveling-card` umstellen.
  (`type:` in der Karten-YAML blieb bei dieser Auslagerung noch
  unverändert - wurde erst später, in `rv-leveling-card` 2.0.0, auf
  `rv-leveling-card` umbenannt, siehe oben.)
- ✅ GitHub Action (`.github/workflows/validate.yml`) validiert bei jedem
  Push/PR: `esphome config` + echter `esphome compile` für beide
  YAML-Dateien, Python-Syntax + JSON-Validität der Integration, sowie
  `hassfest` (offizielle HA-Validierung). **Alle Checks sind aktuell grün.**
- ✅ Integration erfolgreich über **HACS** (als custom repository) bei
  Florian installiert, aktuell Version 0.4.0 (Klimaanlage mit Heizen/
  Kühlen/Presets; Lovelace-Karte separates Repo; Seitenplan mit
  Menü-Editor + Diagnose-Export, siehe "Seitenplan / Seiten-Baukasten"
  oben). Seit
  `v0.1.6` liegt ein `hacs.json` im Repo-Root (Pflichtdatei, fehlte
  vorher – HACS las sie aus dem jeweiligen Release-Tag und lehnte
  Versionen ohne sie ab). Jede Version braucht weiterhin einen echten
  Git-Tag/Release (`gh release create vX.Y.Z`) – gilt jetzt für **beide**
  Repos unabhängig voneinander.
- ✅ Test-Config (`test-esp32-ohne-display.yaml`) fasst inzwischen ALLES
  Nicht-Display-Testbare in einer Firmware zusammen: GY-521-Neigung, die
  Fridolin-Display-Integration (Licht/Klimaanlage/Wetter, rein lesend zur
  Kontrolle) UND die Kühlbox direkt per Bluetooth (Tuya BLE). Damit lässt
  sich alles zusammen mit einer echten Home-Assistant-Instanz testen. Die
  frühere separate `test-kuehlbox-direkt.yaml` ist entfallen (Inhalt hier
  eingeflossen). **Kein `bluetooth_proxy` mehr in dieser Datei** – der
  würde sich mit der eigenen aktiven BLE-Verbindung zur Kühlbox um den
  einzigen Bluetooth-Funk des ESP32 streiten.
- ✅ Kühlbox direkt per Bluetooth bei Florian erfolgreich getestet (Werte
  lesen, Steuerung) – auf dem *alten* `test-kuehlbox-direkt.yaml`, das
  jetzt in `test-esp32-ohne-display.yaml` aufgegangen ist. Nach dem Merge
  nicht erneut auf echter Hardware bestätigt, nur lokal kompiliert.
- ⏳ Kurzer Ausflug zum Waveshare **ESP32-S3-Touch-LCD-7B (1024×600)**
  (siehe Git-Historie, u.a. Commit "Display: Umstieg auf Waveshare
  ESP32-S3-Touch-LCD-7B") – wieder verworfen, Florian bleibt beim
  800×480-Board. Alle Seiten (Übersicht, Nivellierung) sind wieder auf
  800×480 zurückgebaut und lokal kompiliert, aber **noch nicht auf
  echter 800×480-Hardware geflasht/gesehen**.
- ⏳ **Klimaanlagen-Seite (Heizen/Kühlen/Presets) und der zweifarbige
  Ring sind neu und ungetestet** – weder auf echter Hardware noch gegen
  eine echte Klimaanlagen-Entity in Home Assistant. Die drei Presets
  (`eco`/`normal`/`max`) werden 1:1 an die Zielentität durchgereicht;
  ob die echte Klimaanlage genau diese drei Werte kennt, ist offen.
- ⏳ **Lovelace-Karte (`rv-leveling-card`, eigenes Repo)**: Visuell in
  einer lokalen Browser-Vorschau (Fake-`hass`-Objekt, kein echtes Home
  Assistant, auch auf iPhone-Breite 375px geprüft) durchgetestet –
  Wohnwagen- und Wohnmobil-Grafik, Live-Umschalten per Editor, Blasen-
  Bewegung, "Nullen"-Button-Service-Call, UI-Karteneditor (`ha-form`)
  funktionieren dort alle. **Noch nicht als eigenständiges HACS-
  Dashboard-Repo bei Florian installiert/in einem echten HA-Dashboard
  gerendert**, und die Standard-Entity-IDs sind jetzt bewusst leer
  (kein Fridolin-spezifischer Rate-Default mehr, da das Repo öffentlich
  für beliebige Nutzer ist) – müssen im Karteneditor gesetzt werden. Karte
  wurde inzwischen umbenannt (`rv-leveling-card` statt
  `fridolin-nivellierung-card`, Version 2.2.0, i18n für 8 Sprachen) und
  ein PR gegen `hacs/default` ist offen
  ([hacs/default#11341](https://github.com/hacs/default/pull/11341)), um
  sie ganz ohne Custom-Repository-Eintrag im offiziellen HACS-Store
  auffindbar zu machen – **noch nicht gemerged**, Status per
  `gh pr view 11341 --repo hacs/default --json state,mergedAt` prüfbar.
- ⏳ **Wohnmobil-Grafik auf dem Display** (`img_wohnmobil`,
  Einstellungen-Umschalter) ist neu und nur lokal kompiliert – noch nicht
  auf echter Hardware gesehen.
- ❌ Noch nicht gegen eine echte Home-Assistant-Instanz mit echten
  Lichtern/Klimaanlage/Wetterdaten *im Livebetrieb* durchgetestet (nur
  Kühlbox + Neigungssensor bestätigt) – der Rest nur syntaktisch/per
  Compile validiert.
- ✅ **Umlaute behoben**: eigene `font:`-Deklaration (Google Font
  Montserrat über ESPHomes Font-Renderer statt LVGLs eingebauter
  ASCII-only-Bitmap-Fonts, siehe "Wichtige technische Details") unter
  denselben IDs (`montserrat_14/20/28/40`) wie vorher - ä/ö/ü/Ä/Ö/Ü/ß
  erscheinen jetzt korrekt, die ASCII-Ersatzschreibweise "Kuehlbox" ist
  entfallen (jetzt "Kühlbox", auch in den HA-Entity-Namen). Nur lokal
  kompiliert, noch nicht auf echter Hardware gesehen.
- ✅ **Verbindungs-Hinweis auf der Übersichtsseite**: `box_verbindung_verloren`
  wird sichtbar, sobald die API-Verbindung zu Home Assistant abbricht
  (`api: on_client_connected`/`on_client_disconnected`), damit eingefrorene
  Wetter-/Licht-/Klimaanlage-Werte nicht unbemerkt als aktuell erscheinen.
  Start-Zustand optimistisch "verbunden". Nur lokal kompiliert.
- ✅ **`safe_mode:` ergänzt** (zusätzlich zu ESP-IDFs ohnehin schon aktivem
  App-Rollback über die zwei OTA-Partitionen app0/app1, siehe "Wichtige
  technische Details"): nach 5 erfolglosen Boots in Folge (jeweils ohne
  WLAN/API-Verbindung innerhalb von 2 Minuten) startet das ESP in einen
  minimalen WLAN+OTA-Modus, über den sich per Netzwerk wieder eine
  funktionierende Firmware aufspielen lässt.
- ✅ **`esphome/apply_page_plan_from_ha.py`**: zieht den Seitenplan direkt
  per Home-Assistant-REST-API (Diagnose-Endpunkt + automatische
  Config-Entry-Suche über einen Long-Lived Access Token) und ruft
  `generate_display_yaml.py` in einem Rutsch auf - erspart den bisherigen
  manuellen Weg "Diagnose herunterladen" -> Datei speichern -> Generator
  von Hand aufrufen. Dabei auch `_load_plan`/`extract_page_plan()` im
  Generator selbst korrigiert: erkennt jetzt zusätzlich das ECHTE Format
  von HAs eingebautem "Diagnose herunterladen"-Knopf (Seitenplan liegt
  dort unter `data.page_plan`, umschlossen von `home_assistant`/
  `custom_components`/`integration_manifest` - vorher wurde nur ein
  Seitenplan auf oberster Ebene erkannt, was beim echten HA-Download real
  nie zugetroffen hätte). End-to-End gegen einen selbstgebauten
  Mock-HTTP-Server getestet (Entry-Suche, Diagnose-Abruf, Token-Fehler,
  Verbindungsfehler) - kein echtes Home Assistant nötig für den Test,
  Byte-für-Byte-Vergleich mit dem `--check`-Selbsttest bestätigt.
- ✅ **Neigungswerte geglättet**: `median` (Ausreisser wie kurze Stöße/
  Vibration herausfiltern) + `exponential_moving_average` (Rest glätten,
  `alpha: 0.2`) auf `accel_x`/`accel_y`/`accel_z` (MPU6050) - wirkt VOR der
  `atan2()`-Berechnung, beide Neigungswerte UND der per "Nullen"-Knopf
  übernommene Nullpunkt profitieren automatisch mit, ohne dass die
  Berechnung selbst angefasst wurde. Reale Änderung macht sich nach ca.
  1-2s bemerkbar statt sofort. Nur lokal kompiliert (RAM/Flash
  unverändert) - Wirkung auf echtes Wackeln/Vibration erst mit echter
  Hardware im Wohnwagen beurteilbar, Filter-Parameter (`window_size: 5`,
  `alpha: 0.2`) ggf. nach dem Livetest nachjustieren.

## Bekannte Einschränkungen

- Klimaanlagen-Entity (`climate.fridolin_heizung`) unterstützt Heizen,
  Kühlen, Aus sowie einen festen Eco/Normal/Max-`preset_mode` – kein
  Auto-Modus, keine Lüfterstufen. Presets werden ungeprüft durchgereicht.
- Die Integration ist für **genau ein Display / einen Wohnwagen**
  ausgelegt (`async_set_unique_id(DOMAIN)` erzwingt eine einzige Instanz).
- Bis zu 4 Licht-Slots, nicht mehr.

## Wichtige technische Details (falls relevant für Folgearbeiten)

- **API-Encryption-Key**: `esphome/secrets.yaml` braucht einen echten
  32-Byte-Base64-Key (`openssl rand -base64 32`). Ein all-zero-Key wird
  von ESPHome explizit abgelehnt ("reserved and provides no protection").
- **GitHub Actions Bash-Steps laufen mit `set -e`**: Falls du im
  CI-Workflow selbst debuggen/Fehler abfangen willst, brauchst du
  `set +e` um den kritischen Teil, sonst bricht die Shell ab, bevor
  eigene Fehlerbehandlung/Annotationen laufen.
- **HACS braucht einen echten Git-Tag/Release** (nicht nur eine
  `version` in der `manifest.json`), um eine Version installierbar zu
  machen. Bei künftigen Änderungen: `version` in `manifest.json`
  hochzählen, committen, dann einen passenden Git-Tag + GitHub-Release
  anlegen (per `gh release create vX.Y.Z`).
- `manifest.json`'s `documentation`-Feld darf bei Custom-Integrationen
  **nicht** auf `home-assistant.io` zeigen (hassfest lehnt das ab) –
  muss auf die eigene Repo-URL zeigen.
- **LVGL-Fonts unter ESPHome**: die "magischen" Kurznamen wie
  `montserrat_14/20/28/40` sind nur ein Fallback - referenziert man sie in
  `text_font:`, OHNE sie selbst zu deklarieren, generiert ESPHome
  automatisch LVGLs eingebaute Bitmap-Fonts (reines ASCII, keine Umlaute).
  Deklariert man dagegen selbst einen `font:`-Eintrag mit exakt dieser ID
  (z.B. `file: "gfonts://Montserrat", id: montserrat_14, size: 14`), nutzt
  LVGL automatisch diesen statt den eingebauten Shortcut zu erzeugen -
  gleiches Aussehen, aber mit frei waehlbarem `glyphs:`-Zeichensatz. Ein
  `glyphs:`-Eintrag ERSETZT die Default-ASCII-Liste komplett statt sie zu
  ergaenzen, deshalb muss man dort den vollen gewuenschten Zeichensatz
  (ASCII + Umlaute + Sonderzeichen) explizit auflisten, am einfachsten als
  YAML-Anchor (`&name`) einmal definiert und in den anderen Font-Groessen
  per `*name` wiederverwendet. Emoji-artige Symbole wie "⚙" sind in
  normalen Text-Schriftarten (auch Google Fonts wie Montserrat) NICHT
  enthalten und fuehren zu einem klaren Compile-Fehler ("missing 1 glyph")
  statt eines stillen Fallbacks - fuer sowas lieber ein eigenes kleines
  SVG-Icon bauen (siehe `images/zahnrad.svg`) statt nach einer Schriftart
  mit dem passenden Glyph zu suchen.
- **Der YAML-Generator hat eigene, hartkodierte Text-Anker** (z.B.
  `name: "Kühlbox Batterie"` in `REMOVE_ITEM_ANCHORS`/Aequivalenten in
  `generate_display_yaml.py`), die exakt zum Text in
  `wohnwagen-display.yaml` passen muessen. Aendert man sichtbaren Text in
  der YAML (z.B. einen Namen/Titel), IMMER mit `grep` nach dem alten Text
  in `generate_display_yaml.py` suchen und die Anker mit aktualisieren -
  sonst bricht `strip_page_fragments()` beim Seiten-Weglassen mit einem
  klaren `ParseError` ab (kein stiller Fehler, aber leicht zu uebersehen,
  ist beim Umbenennen "Kuehlbox" -> "Kühlbox" in dieser Session genau so
  passiert und wurde erst durch den echten `--check`/`--plan`-Testlauf
  gefunden).
- **ESPHome-Board-Wechsel** (falls nochmal nötig): Das 800×480-Board
  braucht `ch422g:` als IO-Expander, `display: platform: mipi_rgb, model:
  ESP32-S3-TOUCH-LCD-7-800X480`, Backlight als einfacher `switch:
  platform: gpio`. Das 7B-Board (1024×600) braucht stattdessen
  `waveshare_io_ch32v003:`, `model: RPI` mit expliziten Timing-Werten
  (siehe Git-Historie, Commit "Display: Umstieg auf Waveshare
  ESP32-S3-Touch-LCD-7B"), und die Backlight ist dort eine dimmbare
  `light:`-Entity statt eines einfachen Schalters. Beide Boards nutzen
  denselben `esp32:`-Kern (ESP32-S3, esp-idf), aber mit leicht
  unterschiedlichen `sdkconfig_options`/`framework.advanced`-Einträgen –
  am einfachsten den kompletten Block aus der Git-Historie kopieren
  statt einzelne Werte zu ändern.
- Die Datei `home-assistant-standort-wetter.yaml` (ältere REST/Jinja-
  Lösung für Standort+Wetter) ist **veraltet und obsolet**, wurde durch
  die Custom-Integration komplett ersetzt und liegt nicht im Repo.

## Offene Aufgaben / mögliche nächste Schritte

1. Test-Config (`test-esp32-ohne-display.yaml`) bei Florian erneut über
   das ESPHome-Add-on flashen (nach dem Merge mit der Kühlbox) und
   prüfen, ob weiterhin alles funktioniert – insbesondere, dass
   `bluetooth_proxy` fehlt jetzt niemanden fehlt, den Florian eigentlich
   noch wollte.
2. Klimaanlagen-Seite gegen eine echte `climate`-Entity mit Heizen/Kühlen
   und Eco/Normal/Max-Presets testen; ggf. Preset-Namen anpassen, falls
   die echte Klimaanlage andere Bezeichnungen erwartet.
3. `rv-leveling-card` installieren: entweder jetzt schon als Custom
   Repository (Kategorie "Dashboard") in HACS eintragen, oder auf den
   Merge von [hacs/default#11341](https://github.com/hacs/default/pull/11341)
   warten und dann ganz normal über die HACS-Suche installieren. Danach
   alte Dashboard-Ressource
   (`/fridolin_display/fridolin-nivellierung-card.js`) durch die neue
   ersetzen, Entity-IDs im Karteneditor setzen (keine Vorbelegung mehr).
4. Wohnwagen/Wohnmobil-Umschalter auf der Einstellungsseite des Displays
   auf echter Hardware testen (Grafik-Wechsel, Persistenz nach Neustart).
5. Sobald das alles läuft: reales 800×480-Waveshare-Display besorgen,
   verkabeln, `wohnwagen-display.yaml` flashen, komplette UI live testen –
   das betrifft inzwischen auch alles noch nicht auf echter Hardware
   Gesehene: die neue Umlaut-Schriftart, den Verbindungs-Hinweis, den
   Zahnrad-Icon-Button und `safe_mode:`.
6. Ggf. Kleinigkeiten aus dem Livetest nachjustieren (Pinbelegung, Timing,
   Layout).

## Ton/Stil-Hinweis

Florian ist technisch versiert (kennt sich mit ESPHome, Home Assistant,
Netzwerken aus), spricht Deutsch, mag pragmatisches, direktes Vorgehen
("Wir bauen gleich mal die ganze Integration" statt erst lange zu planen).
Commits/PRs auf Deutsch kommentieren, wie bisher im Repo üblich.
