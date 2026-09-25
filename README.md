# Fridolin Display

Touch-Oberfläche für den Wohnwagen "Fridolin": ein Waveshare
ESP32-S3-Touch-LCD-7 (800×480, kapazitiver Touch) mit ESPHome/LVGL,
plus eine eigene Home-Assistant-Integration, über die sich alle
angezeigten Entitäten (Licht, Heizung, Standort, Wetter) bequem in der
Home-Assistant-Oberfläche zuordnen lassen, ohne den ESP32 neu flashen
zu müssen.

## Inhalt dieses Repos

- **`esphome/wohnwagen-display.yaml`** – die ESPHome-Konfiguration für
  das Display: vier wischbare Seiten (Übersicht mit Wetter, Licht,
  Heizung, Nivellierung mit GY-521-Neigungssensor) plus eine
  Einstellungsseite als Overlay.
- **`esphome/secrets.yaml.example`** – Vorlage für die
  WLAN-/API-Zugangsdaten. Kopieren nach `secrets.yaml` und mit echten
  Werten füllen (diese Datei ist in `.gitignore`, landet also nie im
  Repo).
- **`esphome/test-esp32-ohne-display.yaml`** – schlanke Testkonfiguration
  ohne Display/Touch, für einen "nackten" ESP32-Devkit mit angeschlossenem
  GY-521. Prüft unabhängig vom Display, ob der Neigungssensor plausible
  Werte liefert und ob die Verbindung zur Home-Assistant-Integration
  (WLAN, verschlüsselte API, Licht-/Heizungs-/Wetterwerte) funktioniert.
- **`custom_components/fridolin_display/`** – die Home-Assistant-Integration.
  Details und Installationsanleitung in deren eigener
  [README](custom_components/fridolin_display/README.md).

## Architektur in Kürze

Das Display spricht immer nur mit einer festen Handvoll Entities der
Integration (`light.fridolin_licht_1`, `climate.fridolin_heizung`,
`sensor.fridolin_wetter_*`, …). Welche echten Geräte dahinterstecken,
stellt man über die Options-Seite der Integration in Home Assistant
ein – Änderungen wirken sofort, ohne den ESP32 neu zu flashen.

## Stand / bekannte Einschränkungen

- Noch nicht gegen eine echte Home-Assistant-Instanz getestet.
- Heizungs-Entity unterstützt nur Heizen an/aus + Zieltemperatur.
- Für genau einen Wohnwagen/ein Display ausgelegt.

Siehe auch die Commit-Historie für den Entstehungsverlauf.
