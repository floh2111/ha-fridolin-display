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
| `climate.fridolin_heizung` | Heizung |
| `sensor.fridolin_wetter_zustand` / `_temperatur` | aktuelles Wetter |
| `sensor.fridolin_wetter_h0_zeit/_temp/_zustand` … `h3_*` | Stunden-Vorhersage |
| `sensor.fridolin_wetter_morgen_min/_max/_zustand` | Ausblick auf morgen |
| `sensor.fridolin_standort_status` | Zeitpunkt der letzten Standortübernahme |
| `button.fridolin_standort_uebernehmen` | von der Einstellungsseite aufgerufen |

Änderst du in den Integrations-Optionen, welches echte Licht z.B.
hinter "Licht 1" steckt, wirkt sich das sofort aufs Display aus.

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

## Grenzen dieser ersten Version

- Es wurde nicht gegen eine echte Home-Assistant-Instanz getestet
  (in dieser Umgebung stand keine zum Testen zur Verfügung) – die
  Grundstruktur folgt den üblichen Mustern für Custom Components
  (ConfigFlow, OptionsFlow, DataUpdateCoordinator, CoordinatorEntity),
  ein erster Testlauf bei dir ist trotzdem sinnvoll.
- Die Heizungs-Entity unterstützt nur "Heizen an/aus" +
  Zieltemperatur, keine weiteren HVAC-Modi (Kühlen, Auto, …).
- Pro Instanz gibt es genau ein Display (`await
  self.async_set_unique_id(DOMAIN)` verhindert eine zweite Instanz).
  Für einen zweiten Wohnwagen bräuchte es eine kleine Anpassung.
