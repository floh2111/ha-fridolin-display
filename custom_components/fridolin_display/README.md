# Fridolin Display (Custom Integration)

Konfigurierbare Gegenstelle für das Wohnwagen-Touch-Display: Du wählst
über die normale Home-Assistant-Oberfläche, welche echten Lichter,
welche Heizung und welcher Standort-Tracker hinter dem Display stecken
– ganz ohne den ESP32 neu zu flashen.

## Funktionsprinzip

Der ESP32 spricht immer nur mit einer festen Handvoll Entities dieser
Integration:

| Display-Entity | Zweck |
|---|---|
| `light.fridolin_licht_1` … `_4` | Licht-Slots der ersten Licht-Seite (nur belegte Slots werden angelegt) |
| `climate.fridolin_heizung` | Klimaanlage der ersten Klimaanlagen-Seite (Heizen/Kühlen/Aus, Eco/Normal/Max) |
| `sensor.fridolin_wetter_zustand` / `_temperatur` / `_icon` | aktuelles Wetter |
| `sensor.fridolin_wetter_h0_zeit/_temp/_zustand/_icon` … `h3_*` | Stunden-Vorhersage |
| `sensor.fridolin_wetter_morgen_min/_max/_zustand/_icon` | Ausblick auf morgen |
| `sensor.fridolin_standort_status` | Zeitpunkt der letzten Standortübernahme |
| `button.fridolin_standort_uebernehmen` | von der Einstellungsseite aufgerufen |

Änderst du in den Integrations-Optionen, welches echte Licht z.B.
hinter "Licht 1" steckt, wirkt sich das sofort aufs Display aus.

## Seitenplan (welche Seiten das Display zeigt)

Seit Version 0.3.0 legt ein **Seitenplan** fest, welche Seiten das
Display in welcher Reihenfolge zeigt – einstellbar über "Konfigurieren"
→ erster Schritt (JSON-Liste, siehe `page_plan.py`). Mögliche
Seiten-Typen: `overview`, `light`, `climate`, `leveling`, `fridge`,
`sensors` (`sensors` ist als Typ bereits vorbereitet, hat aber noch
keine eigene Entity-Erzeugung/Display-Seite – folgt später). `light`
und `climate` können **mehrfach** im Plan vorkommen (z.B. zwei
Klimazonen) – jede weitere Instanz bekommt eigene, instanz-
parametrisierte Entity-IDs (`climate.fridolin_climate_2`,
`light.fridolin_licht_2_1` usw.), die erste Instanz behält aus
Kompatibilitätsgründen die alten IDs (`climate.fridolin_heizung`,
`light.fridolin_licht_1`).

**Wichtig:** Der Seitenplan wirkt aktuell **nur auf die HA-Seite**
(welche Entities angelegt werden) – die ESP32-Firmware selbst zeigt
weiterhin die fest verdrahteten 5 Seiten aus `wohnwagen-display.yaml`
in fester Reihenfolge. Ein Generator, der aus dem Seitenplan die
passende `wohnwagen-display.yaml` erzeugt (sodass Reihenfolge/Auswahl
der Seiten nach einem Reflash tatsächlich dem Plan folgen), ist der
nächste Ausbauschritt und noch nicht fertig. Solange du den Seitenplan
nicht änderst (Standard entspricht genau dem bisherigen Display),
ändert sich für dich nichts.

Die Entity-Zuordnung (welches echte Licht/welche echte Klimaanlage
hinter einer Seite steckt) ist im zweiten Options-Schritt weiterhin
sofort wirksam, ohne Reflash.

Die `_icon`-Sensoren liefern einen von 16 festen Schlüsseln (`sunny`,
`clear-night`, `partlycloudy`, `partly-cloudy-night`, `cloudy`, `rainy`,
`pouring`, `snowy`, `snowy-rainy`, `lightning`, `lightning-rainy`, `fog`,
`hail`, `windy`, `windy-variant`, `exceptional`), abgeleitet aus dem
OpenWeatherMap-Wettercode (`coordinator.py`, `_map_icon`). Sie dienen nur
dem Display: Das ESP32 wählt darüber sein Icon aus `esphome/images/weather/`
(gleichnamige SVG-Dateien). Für Home Assistant selbst ändert sich nichts.

## Installation

1. Diesen ganzen Ordner (`fridolin_display`) nach
   `<dein-home-assistant-config-verzeichnis>/custom_components/fridolin_display/`
   kopieren.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen →
   "Fridolin Display" suchen.
4. Im Einrichtungsdialog: deinen Standort-Tracker (die
   `device_tracker`-Entity deiner Home-Assistant-App) und deinen
   OpenWeatherMap-API-Key eintragen.
5. Auf der Integrationskarte "Konfigurieren" klicken und dort
   festlegen, welche echten Licht- und Heizungs-Entities hinter den
   Display-Slots stecken. Nicht benötigte Licht-Slots einfach leer
   lassen.

## Wichtig für die ESPHome-Datei

Die `wohnwagen-display.yaml` muss auf die neuen, festen Entity-IDs
dieser Integration zeigen (siehe Tabelle oben) statt auf die
ursprünglichen `light.wohnwagen_licht_1` / `climate.wohnwagen_heizung`
/ die REST-basierten Wettersensoren. Eine bereits angepasste Version
liegt bei.

Die Datei `home-assistant-standort-wetter.yaml` (REST-Sensoren +
Jinja-Templates) wird durch diese Integration ersetzt und kann
gelöscht werden, sobald die Integration läuft.

## Lovelace-Karte für die Nivellierung

Die Dashboard-Karte für die Nivellierung (Kreuzlibelle auf einem
Wohnwagen-/Wohnmobil-Grundriss) ist **kein Teil dieser Integration
mehr** – sie lebt seit Version 0.2.0 in einem eigenen Repository:
[floh2111/rv-leveling-card](https://github.com/floh2111/rv-leveling-card),
als eigenständiges HACS-Dashboard-Repository installierbar. Dort auch
die Einrichtungsanleitung.

Falls du die Karte schon vor 0.2.0 eingebunden hattest: Die alte
Ressourcen-URL `/fridolin_display/fridolin-nivellierung-card.js`
funktioniert nicht mehr (die Integration liefert keine statischen
Dateien mehr aus). Einmalig die Dashboard-Ressource entfernen und durch
die neue aus `rv-leveling-card` ersetzen (siehe dessen README) – deine
Karten-Konfiguration in den Dashboards selbst muss dabei **nicht**
geändert werden, der Karten-Typ heißt weiterhin
`custom:fridolin-nivellierung-card`.

## Grenzen dieser ersten Version

- Es wurde nicht gegen eine echte Home-Assistant-Instanz getestet
  (in dieser Umgebung stand keine zum Testen zur Verfügung) – die
  Grundstruktur folgt den üblichen Mustern für Custom Components
  (ConfigFlow, OptionsFlow, DataUpdateCoordinator, CoordinatorEntity),
  ein erster Testlauf bei dir ist trotzdem sinnvoll.
- Die Klimaanlagen-Entity (`climate.fridolin_heizung`) unterstützt Heizen,
  Kühlen, Aus sowie einen festen Eco/Normal/Max-Modus als `preset_mode`
  (`eco`/`normal`/`max`, 1:1 an die Zielentität durchgereicht - die muss
  diese drei Presets selbst kennen, sonst tut der Knopf nichts). Kein
  Auto-Modus, keine Lüfterstufen.
- Pro Instanz gibt es genau ein Display (`await
  self.async_set_unique_id(DOMAIN)` verhindert eine zweite Instanz).
  Für einen zweiten Wohnwagen bräuchte es eine kleine Anpassung.
