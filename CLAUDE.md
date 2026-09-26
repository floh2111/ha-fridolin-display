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
ESP32-S3-Touch-LCD-7B** (1024×600, GT911-Touch mit 5 Punkten, ESP32-S3,
8 MB PSRAM, 16 MB Flash, IO-Expander CH32V003 auf 0x24, mit Bluetooth), mit
**ESPHome + LVGL** (ESPHome 2026.9). Frühere Versionen der Config waren für
das 800×480-Board "ESP32-S3-Touch-LCD-7" geschrieben (siehe Git-Historie). Das Display hängt am
Wohnwagen, der Wohnwagen ist per VPN-Router mit Florians Heimnetz und
seiner **Home Assistant**-Instanz verbunden.

Nur der Neigungssensor (**GY-521 / MPU6050**) ist physisch direkt am
ESP32 verbaut. Alle anderen Entitäten (Lichter, Heizung) sind echte,
bereits existierende Home-Assistant-Entitäten – das Display steuert sie
nur fern, simuliert nichts lokal.

## Architektur (wichtig!)

Damit sich alles, was auf dem Display angezeigt wird (welches Licht,
welche Heizung, welcher Standort-Tracker), **über die Home-Assistant-UI
konfigurieren lässt statt hart in der ESPHome-YAML verdrahtet zu sein**,
gibt es eine **selbstgeschriebene Home-Assistant-Custom-Integration**
(`custom_components/fridolin_display/`). Sie funktioniert als
Proxy-/Spiegel-Schicht:

- Der ESP32 spricht **immer nur mit einer festen Handvoll Entities**
  dieser Integration (`light.fridolin_licht_1` … `_4`,
  `climate.fridolin_heizung`, `sensor.fridolin_wetter_*`,
  `sensor.fridolin_standort_status`, `button.fridolin_standort_uebernehmen`).
- Über die **Options-Seite der Integration** in Home Assistant stellt
  Florian ein, welche **echten** Licht-/Heizungs-Entities dahinterstecken.
  Das wirkt sofort, ohne den ESP32 neu zu flashen.
- Ein eigener `DataUpdateCoordinator` holt Wetterdaten (aktuell +
  Stundenvorhersage + morgen) direkt von **OpenWeatherMap**, Standort
  kommt von einem `device_tracker` (Home-Assistant-App) oder wird über
  einen Button ("Standort übernehmen") manuell fixiert.

Genaue Entity-ID-Tabelle und Funktionsweise stehen in
`custom_components/fridolin_display/README.md`.

## Repo-Struktur

```
esphome/wohnwagen-display.yaml       – volle Display-Konfiguration für das 7B (5 Wisch-Seiten + Einstellungs-Overlay)
esphome/test-kuehlbox-direkt.yaml    – Testkonfig: Kühlbox direkt per Tuya-BLE (ohne Home Assistant)
esphome/secrets.yaml.example         – Vorlage für WLAN/API-Key (echte secrets.yaml ist gitignored)
esphome/test-esp32-ohne-display.yaml – schlanke Testkonfig ohne Display: GY-521 + HA-API-Check + Bluetooth-Proxy
esphome/fridolin-vorschau.html       – interaktive Browser-Vorschau der UI (auch als Artifact veröffentlicht)
custom_components/fridolin_display/  – die Home-Assistant-Integration (ConfigFlow, OptionsFlow, Coordinator, Entities)
.github/workflows/validate.yml       – CI: `esphome config` + echter `esphome compile` aller drei Configs, hassfest für die Integration
```

## UI-Struktur (ESPHome/LVGL)

Fünf Seiten als Wisch-Karussell (LVGL `tileview`) plus eine Einstellungsseite, die NICHT im
Wisch-Karussell hängt, sondern nur über einen kleinen Zahnrad-Button auf
der Übersichtsseite erreichbar ist (LVGL `top_layer:`):

1. **Übersicht** – aktuelles Wetter, Stundenvorhersage (4 Slots), kurzer
   Blick auf morgen. Zahnrad-Button oben führt zu "Einstellungen".
2. **Licht** – An/Aus-Schalter für die konfigurierten Lichter.
3. **Heizung** – An/Aus + Zieltemperatur für die climate-Entität.
4. **Nivellierung** – zwei "Wasserwaagen" (links/rechts, vorne/hinten),
   berechnet aus dem GY-521 per `atan2` auf die Beschleunigungswerte.
5. **Kühlbox** – runde Zieltemperatur-Anzeige mit −/+, Ein/Aus, Modus MAX/ECO,
   Batterieschutz L/M/H. Die Kühlbox (Euhomy Car Fridge CF, Tuya-BLE, Kategorie
   `xbx`) wird **direkt vom ESP** per Bluetooth gelesen/gesteuert, ohne Home
   Assistant, über die externe Komponente `floh2111/esphome-tuya-ble-fridolin`
   (Fork von Noneawe/BillyNate, auf einen Commit gepinnt). Nur eine BLE-Verbindung
   zur Kühlbox möglich: Tuya-App und HA-Integration "Tuya BLE" müssen aus sein.
6. **Einstellungen (Overlay, nicht wischbar)** – Button "Standort
   übernehmen" (nimmt die Koordinaten vom `device_tracker` und setzt sie
   als festen Wetter-Standort), Anzeige des letzten Übernahme-Zeitpunkts,
   "Zurück"-Button.

## Aktueller Stand (Stand: 2026-09-26)

- ✅ ESPHome-Konfiguration fertig geschrieben (`wohnwagen-display.yaml`).
- ✅ Home-Assistant-Integration fertig geschrieben, inkl. ConfigFlow,
  OptionsFlow, Coordinator, Light/Climate/Sensor/Button-Entities.
- ✅ GitHub-Repo `floh2111/ha-fridolin-display` eingerichtet, Push-Zugriff
  funktioniert.
- ✅ GitHub Action (`.github/workflows/validate.yml`) validiert bei jedem
  Push/PR: `esphome config` für beide YAML-Dateien, Python-Syntax +
  JSON-Validität der Integration, sowie `hassfest` (offizielle
  HA-Validierung). **Alle Checks sind aktuell grün.**
- ✅ Integration erfolgreich über **HACS** (als custom repository) bei
  Florian installiert, mit Release-Tag `v0.1.0`.
- ✅ Test-ESPHome-Config (`test-esp32-ohne-display.yaml`) erstellt: ein
  "nackter" ESP32 + GY-521, ohne Display/LVGL, um Neigungssensor und
  HA-API-Verbindung unabhängig vom teuren Display-Board zu testen.
- ⏳ **Nächster Schritt bei Florian:** Test-Config über das
  ESPHome-Builder-Add-on in Home Assistant flashen (Florian macht das
  Flashen bewusst direkt über das Add-on, nicht über die CLI hier).
- ❌ Noch nicht gegen eine echte Home-Assistant-Instanz mit echten
  Lichtern/Heizung/Wetterdaten *im Livebetrieb* durchgetestet – nur
  syntaktisch validiert (py_compile, JSON, hassfest, `esphome config`).
  Diese Session hier hatte keinen Zugriff auf eine echte HA-Instanz.
- ✅ Kühlbox direkt per Bluetooth auf dem Test-ESP32 (`test-kuehlbox-direkt.yaml`)
  bei Florian erfolgreich getestet (Werte lesen, Steuerung).
- ⏳ Umstieg auf das Waveshare **ESP32-S3-Touch-LCD-7B (1024×600)**:
  `wohnwagen-display.yaml` ist dafür umgebaut (Pins/Timing aus der Community-Config
  agillis/esphome-modular-lvgl-buttons, IO-Expander `waveshare_io_ch32v003`),
  kompiliert mit ESPHome 2026.9, aber noch nicht auf dem echten Board geflasht.
  Die Oberfläche ist noch auf 800×480 gelayoutet, Größen ggf. an 1024×600 anpassen.
- ❌ Umlaute (ä, ö, ü, Ü) fehlen vermutlich in den eingebauten LVGL-Schriften;
  neue Seiten nutzen deshalb ASCII-Schreibweise. Bei Kästchen im Display eine
  eigene `font:` mit Umlauten einbinden.

## Bekannte Einschränkungen

- Heizungs-Entity unterstützt nur "Heizen an/aus" + Zieltemperatur, keine
  weiteren HVAC-Modi (Kühlen, Auto, …).
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
  machen. Aktuell: Tag `v0.1.0` auf Commit mit `manifest.json version
  0.1.0`. Bei künftigen Änderungen: `version` in `manifest.json` hochzählen,
  committen, dann einen passenden Git-Tag + GitHub-Release anlegen.
- `manifest.json`'s `documentation`-Feld darf bei Custom-Integrationen
  **nicht** auf `home-assistant.io` zeigen (hassfest lehnt das ab) –
  muss auf die eigene Repo-URL zeigen.
- Die Datei `home-assistant-standort-wetter.yaml` (ältere REST/Jinja-
  Lösung für Standort+Wetter) ist **veraltet und obsolet**, wurde durch
  die Custom-Integration komplett ersetzt und liegt nicht im Repo.

## Offene Aufgaben / mögliche nächste Schritte

1. Test-Config (`test-esp32-ohne-display.yaml`) bei Florian über das
   ESPHome-Add-on flashen und die Werte in Home Assistant prüfen
   (Neigungssensor-Plausibilität, Integration liefert echte Licht-/
   Heizungs-/Wetterwerte).
2. Sobald das läuft: reales Waveshare-Display besorgen, verkabeln,
   `wohnwagen-display.yaml` flashen, die komplette UI live testen.
3. Ggf. Kleinigkeiten aus dem Livetest nachjustieren (Pinbelegung,
   Timing, Layout).
4. Bei jeder inhaltlichen Änderung an der Integration: Version in
   `manifest.json` hochzählen + neuen Git-Tag/Release anlegen, damit
   HACS das Update erkennt.

## Ton/Stil-Hinweis

Florian ist technisch versiert (kennt sich mit ESPHome, Home Assistant,
Netzwerken aus), spricht Deutsch, mag pragmatisches, direktes Vorgehen
("Wir bauen gleich mal die ganze Integration" statt erst lange zu planen).
Commits/PRs auf Deutsch kommentieren, wie bisher im Repo üblich.
