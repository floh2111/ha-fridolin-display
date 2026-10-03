"""Erzwingt CONFIG_SPIRAM_TIMING_TUNING_POINT_VIA_TEMPERATURE_SENSOR=n, obwohl
ESPHomes eigene psram-Komponente diese Option bei Octal-PSRAM @ 120MHz selbst
bedingungslos auf "y" setzt (components/psram/__init__.py, siehe CLAUDE.md
"Wichtige technische Details" fuer die volle Herleitung/den Bootloop, den das
verursacht hat - ohne diesen Fix hier haben wir PSRAM deshalb erstmal auf
80MHz statt 120MHz gedrosselt, was die Bildwiederholrate spuerbar ausbremst).

DEPENDENCIES = ["psram"] sorgt dafuer, dass ESPHome diese Komponente NACH der
psram-Komponente verarbeitet (Topologische Sortierung nach Abhaengigkeiten,
siehe esphome/config.py) - unser add_idf_sdkconfig_option()-Aufruf hier laeuft
also garantiert NACH psrams eigenem und gewinnt (add_idf_sdkconfig_option ist
ein simpler, ungeschuetzter Dict-Write - wer zuletzt schreibt, gewinnt).
"""

import esphome.config_validation as cv
from esphome.components.esp32 import add_idf_sdkconfig_option

DEPENDENCIES = ["psram"]
CONFIG_SCHEMA = cv.Schema({})


async def to_code(config):
    add_idf_sdkconfig_option(
        "CONFIG_SPIRAM_TIMING_TUNING_POINT_VIA_TEMPERATURE_SENSOR", False
    )
