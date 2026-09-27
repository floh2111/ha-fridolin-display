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
| `light.fridolin_licht_1` … `_4` | Licht-Slots (nur belegte Slots werden angelegt) |
| `climate.fridolin_heizung` | Klimaanlage (Heizen/Kühlen/Aus, Eco/Normal/Max) |
| `sensor.fridolin_wetter_zustand` / `_temperatur` / `_icon` | aktuelles Wetter |
| `sensor.fridolin_wetter_h0_zeit/_temp/_zustand/_icon` … `h3_*` | Stunden-Vorhersage |
| `sensor.fridolin_wetter_morgen_min/_max/_zustand/_icon` | Ausblick auf morgen |
| `sensor.fridolin_standort_status` | Zeitpunkt der letzten Standortübernahme |
| `button.fridolin_standort_uebernehmen` | von der Einstellungsseite aufgerufen |

Änderst du in den Integrations-Optionen, welches echte Licht z.B.
hinter "Licht 1" steckt, wirkt sich das sofort aufs Display aus.

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

Die Integration liefert außerdem eine eigene Dashboard-Karte
(`www/fridolin-nivellierung-card.js`), die dieselbe Kreuzlibelle wie die
Nivellierungs-Seite auf dem Display zeigt – nur auf einem Wohnwagen-
Grundriss mit der **Deichsel nach oben** statt nach rechts (die passendere
Ausrichtung für ein Dashboard). Ein Druck auf "Nullen" in der Karte ruft
denselben `button.press`-Service auf wie der Knopf auf dem Display selbst
– der Nullpunkt wird also **lokal auf dem ESP** gespeichert (übersteht
auch einen Neustart von Home Assistant, weil er im Flash des ESP liegt,
nicht in HA).

Einrichtung:

1. Home Assistant neu starten (die Integration registriert die Karte
   automatisch unter `/fridolin_display/fridolin-nivellierung-card.js`).
2. Einstellungen → Dashboards → oben rechts ⋮ → Ressourcen → Ressource
   hinzufügen. URL: `/fridolin_display/fridolin-nivellierung-card.js`,
   Ressourcentyp: JavaScript-Modul.
3. Karte hinzufügen, z.B. per YAML:
   ```yaml
   type: custom:fridolin-nivellierung-card
   # Nur nötig, falls deine Entity-IDs abweichen (z.B. anderer Gerätename):
   entity_lr: sensor.fridolin_display_neigung_links_rechts
   entity_vh: sensor.fridolin_display_neigung_vorne_hinten
   entity_zero_button: button.fridolin_display_neigung_nullen
   ```
   Die drei Entity-IDs oben sind nur eine **Annahme** (abgeleitet aus dem
   ESPHome-Gerätenamen "Fridolin Display"/"Fridolin Test") – prüfe sie
   unter Einstellungen → Geräte & Dienste → dein ESP32-Gerät → Entitäten,
   und trag bei Abweichung die echten IDs in der Karten-Konfiguration ein.

Die Karte ist rein anzeigend (nicht ziehbar) und aktualisiert sich live,
sobald sich die beiden Neigungs-Sensoren ändern.

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
