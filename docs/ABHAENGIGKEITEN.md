# Abhängigkeiten und Stand der HDMI-Anpassung

Das CMake-Projekt verwendet vier Teile des FRANK-MICRO-Quellcodes:

- `frank-hdmi-sound/src/` (HDMI-Treiber)
- `drivers/fatfs/` (FAT-Dateisystem)
- `drivers/sdcard/` (SPI-SD-Treiber)
- `src/boards/waveshare_rp2350_pizero.h` (Board-Konfiguration)

Die Treiber werden mit `python tools/vendor_frank.py ../frank-micro` als Quellkopie in `third_party/frank-micro/` eingelagert. Die Quellen bleiben einzeln editierbar und sind nach dem Einchecken auf GitHub unabhängig von einem lokalen FRANK-Pfad vorhanden. Von FRANK selbst werden weder BBC-ROMs noch Emulator-Quellen übernommen.

## HDMI-Fix für die RP2350B-GPIOs 32–39

Die ursprüngliche HDMI-Audiobibliothek initialisiert PIO-Pinmasken mit 32 Bit. Für GPIOs 32–39 muss der PIO-GPIO-Basiswert auf 16 gestellt und die Pinmaske über die 64-Bit-PIO-Funktionen gesetzt werden. Der Export prüft diese Stellen und führt die Anpassung gegebenenfalls aus:

- `frank_serialiser.c`: `pio_set_gpio_base(cfg->pio, 16)` zu Beginn der Initialisierung bei `PLATFORM_Z0`.
- `frank_serialiser.pio`: `pio_sm_set_pins_with_mask64` und `pio_sm_set_pindirs_with_mask64`.

Die HDMI-GPIO-Belegung wird per CMake gesetzt: CLK 38, D0 36, D1 34, D2 32. Die Board-Belegung des SD-Backends wird über SPI1-Pins 30, 31, 40, 43 gesteuert.

## FatFs ohne PSRAM

Die Datei `src/fatfs_heap.c` ersetzt `ffsystem.c` aus FRANK. Sie stellt bei dynamischen langen Dateinamen `malloc/free` bereit. Der Player benötigt keinen externen PSRAM-Chip.

## Versionierung

Ein Export aus dem funktionierenden lokalen FRANK-Klon ist einem ungeprüften `main`-Stand vorzuziehen. Die Datei `third_party/frank-micro/SOURCE.md` vermerkt die Upstream-Commit-IDs, sofern die Quelle ein Git-Klon ist. Die exportierten Dateien enthalten keine `.git`-Metadaten und keine lokalen Pfade.

## Lizenzhinweise

Der Player steht unter GPL-3.0-or-later. Die Treiber bleiben unter ihren jeweiligen ursprünglichen Lizenzbedingungen; Copyright- und SPDX-Kommentare nicht entfernen. Der FRANK-HDMI-Treiber ist eine GPL-3.0-basierte Bibliothek; der SD-Treiber und FatFs führen zusätzliche Hinweise im Quellcode. Quellkopien bei öffentlicher Verbreitung zusammen mit diesen Lizenzinformationen bereitstellen.
