# Kühlbox per CarPlay (Home-Assistant-App) bedienen

Voraussetzungen: iPhone mit der Home-Assistant-Companion-App, Auto mit CarPlay,
und eine Verbindung vom Wohnwagen zu Home Assistant (z. B. Cudy LT300 mit SIM
und VPN) - die Befehle laufen über Home Assistant zum ESP im Wohnwagen.

## 1. Skripte in Home Assistant anlegen

`kuehlbox_skripte.yaml` enthält zehn Skripte:

| Skript | Wirkung |
| --- | --- |
| Kühlbox 2 / 4 / 5 / 6 / 7 °C und −18 °C | schaltet die Kühlbox ein und setzt den Sollwert |
| Kühlbox +1 °C / −1 °C | ändert den Sollwert um ein Grad (Grenzen −20 bis 20) |
| Kühlbox MAX / ECO | stellt den Modus um |

1. Datei öffnen, die Entity-IDs prüfen (Suchen/Ersetzen, falls deine anders
   heißen - nachsehen unter *Einstellungen → Geräte & Dienste → ESPHome →
   Fridolin Display → Entities*).
2. Den Inhalt an die `scripts.yaml` in deiner Home-Assistant-Konfiguration
   anhängen (z. B. mit dem Datei-Editor-Add-on) und danach unter *Entwicklerwerkzeuge →
   YAML → Skripte neu laden* ausführen.
3. Zum Testen ein Skript in der Weboberfläche starten: die Zieltemperatur
   auf dem Display muss sich ändern.

## 2. CarPlay in der App einrichten (iPhone)

*Companion-App → Einstellungen → CarPlay*

1. **Schnellzugriff** → Eintrag hinzufügen → die Kühlbox-Entity
   (`switch … kuhlbox_power`, damit Ein/Aus geht) und die Skripte, die du
   brauchst (2 / 4 / 5 / 6 / 7 / −18 °C, +1 / −1, MAX / ECO).
2. Der Reiter **Steuerung** zeigt zusätzlich alle Schalter und Skripte nach
   Typ. Sensoren (Ist-Temperatur) zeigt der offizielle CarPlay-Modus nicht
   auf dem Bildschirm.
3. **Ist-Temperatur per Sprache (ab iOS 26.4):** Unter *Schnellzugriff* einen
   Eintrag vom Typ **Assist** bzw. **Assist-Prompt** hinzufügen, z. B. mit dem
   Text „Wie warm ist die Kühlbox?“. Damit Assist den Wert kennt, muss der
   Temperatursensor der Kühlbox unter *Einstellungen → Sprachassistenten →
   Entities freigeben* für Assist freigegeben sein. Außerdem braucht die
   Assist-Pipeline eine Sprachausgabe (Text-zu-Sprache).
4. Am Auto: CarPlay starten, die Home-Assistant-App öffnen, im Schnellzugriff
   tippen.

## Hinweise

- Beim Fahren muss der Wohnwagen-Router Internet haben (SIM im LT300) und das
  VPN zu Home Assistant stehen, sonst kommen die Befehle nicht an.
- Antwort-Verzögerung: Die Kühlbox bestätigt Änderungen über Bluetooth
  langsam, nach dem Antippen kann es einige Sekunden dauern.
- Sicherheit: Bedienung nur im Stand oder per Sprache/Beifahrer.
