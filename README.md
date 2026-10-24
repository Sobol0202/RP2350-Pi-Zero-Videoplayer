# HDMI-Testplayer für RP2350-PiZero

Kleiner HDMI-Bildschirmtester auf Basis des Waveshare RP2350-PiZero. Die Firmware zeigt nach dem Einschalten automatisch Testbilder und wechselt auf Tastendruck zur Videodatei von der microSD-Karte. Das HDMI-Signal bleibt während des Umschaltens bestehen.

Stand: **V0.3.1 (Bildplayer)**. Auf einem RP2350-PiZero wurde die Bildausgabe einschließlich Wiedergabe einer eigenen `TEST.LOOP`-Datei erfolgreich erprobt. HDMI-Ton ist im Treiber vorbereitet, wird von dieser Player-Version aber noch nicht ausgegeben.

## Funktionen

- HDMI: 640 × 480 bei 60 Hz, Bildinhalt 320 × 240 in RGB332.
- Neun interne Testmuster, jeweils fünf Sekunden; automatische Wiederholung.
- Wiedergabe von `TEST.LOOP` mit 20 fps, Endlosschleife.
- GPIO26 nach GND: Wechsel Testbilder ↔ Video; Video beginnt bei jedem Wechsel am Anfang.
- FAT32-microSD über SPI1, Lesen ohne Schreibzugriffe durch den Player.
- Fehleranzeige auf HDMI bei fehlender Karte, Datei, ungültiger Größe oder Lesefehler.

## Hardware

| Funktion | Anschluss |
|---|---|
| Board | Waveshare RP2350-PiZero (RP2350B) |
| Taster | GPIO26, Stift 37 → GND, Stift 39 |
| HDMI | Mini-HDMI-Buchse (GPIO 32–39, fest auf dem Board verdrahtet) |
| microSD | SPI1, GPIO 30/31/40/43 (auf dem Board verdrahtet) |
| Versorgung | 5 V über normalen USB-C-Anschluss |

Der Taster wird über einen internen Pull-up eingelesen. Bei älteren RP2350-Revisionen kann ein externer Widerstand von 4,7 kΩ nach 3,3 V erforderlich sein. Keine 5 V auf GPIO26 legen.

Die HDMI-Firmware verwendet 252 MHz und eine erhöhte Kernspannung von 1,50 V. Diese Konfiguration liegt außerhalb des regulären Standardtakts. Für Dauerbetrieb sind Temperatur, Stabilität und die Stromaufnahme unter tatsächlicher Videolast zu prüfen. Die vorgesehenen maximal 500 mA sind noch nicht für jeden Betriebszustand nachgewiesen.

## Projektaufbau

```text
RP2350_HDMI_Testplayer_GitHub/
├── CMakeLists.txt            Firmware-Build
├── src/                      Player und FatFs-SRAM-Anbindung
├── tools/                    Medienkonverter, Prüfung, Treiberexport
├── media/DEMO_10S.LOOP       kleine synthetische Demo (kein Fremdvideo)
├── third_party/frank-micro/  Treiber-Snapshot nach dem Export
├── docs/                     Datenformat und Abhängigkeiten
├── .gitignore
└── LICENSE
```

## Build (Windows, Git Bash)

Voraussetzungen: Pico SDK 2.3.1, Arm GNU Toolchain für `arm-none-eabi`, CMake, Ninja, Git und ein nativer Windows-C/C++-Compiler für `pioasm`/`picotool`. Für Medienkonvertierung zusätzlich Python 3 und FFmpeg/FFprobe.

### 1. Treiber ins Repository übernehmen

Da die HDMI-Anpassungen auf einem lokal bereits funktionierenden FRANK-Klon basieren, sollte **dieser Stand** verwendet werden. Das Skript übernimmt ausschließlich die benötigten Treiber und Board-Dateien, setzt gegebenenfalls die beiden Z0-PIO-Korrekturen und kopiert keine Git-Metadaten:

```bash
cd RP2350_HDMI_Testplayer_GitHub
python tools/vendor_frank.py ../frank-micro
```

Alternativ ohne vorhandenen Klon:

```bash
python tools/fetch_frank.py
```

Der Downloadpfad verwendet den aktuellen `main`-Stand von FRANK. Für einen nachweislich identischen Build den Commit mit `--ref <COMMIT>` festlegen oder den erprobten lokalen Quellstand exportieren. Versionsangaben der kopierten Treiber werden in `third_party/frank-micro/SOURCE.md` dokumentiert.

**Für GitHub:** `third_party/frank-micro/` nach dem Export mit einchecken. Dadurch sind sämtliche von der Firmware benötigten FRANK-Quellen im Repository vorhanden. Das Pico SDK und die Compiler bleiben externe Werkzeuge.

### 2. Umgebung konfigurieren

Keine festen Benutzerpfade in den Projektdateien. Das SDK wird über `PICO_SDK_PATH` gefunden; bei Bedarf wird die ARM-Toolchain über `PICO_TOOLCHAIN_PATH` gesetzt. Beispiel mit Platzhalter `USER`:

```bash
export PICO_SDK_PATH="C:/Users/USER/pico-sdk-2.3.1"
export PICO_TOOLCHAIN_PATH="C:/Tools/arm-gnu-toolchain-arm-none-eabi"
```

**Hinweis:** `USER` steht nur für einen Platzhalter. Wird eine andere Ordnerstruktur verwendet, sind ausschließlich die beiden Variablen entsprechend anzupassen. Im Projekt selbst sind keine persönlichen absoluten Pfade hinterlegt. Ninja sowie der native Compiler (`gcc`/`g++`) müssen im `PATH` stehen.

### 3. Firmware bauen

```bash
cmake -S . -B build -G Ninja
cmake --build build --parallel 4
```

Ausgabe: `build/pico_hdmi_player.uf2`. Anschließend BOOTSEL-Modus aktivieren und die UF2 auf das vom RP2350 bereitgestellte Laufwerk kopieren. Die Firmware startet ohne weitere Eingaben.

## microSD und Bedienung

1. microSD-Karte mit FAT32 formatieren.
2. `TEST.LOOP` im **Hauptverzeichnis** ablegen (nicht im Ordner `micro/`). Für einen schnellen Test `media/DEMO_10S.LOOP` in `TEST.LOOP` umbenennen.
3. Karte bei ausgeschalteter Platine einstecken und USB-Strom anlegen.
4. Nach dem Start läuft die Testbildfolge. GPIO26 kurz mit GND verbinden und wieder lösen: Videomodus. Erneutes Betätigen: Testbilder.

Die Wechselerkennung ist auf 40 ms entprellt. Die Datei wird im Videomodus von Anfang an gelesen und am Ende wieder geöffnet beziehungsweise an den Anfang zurückgesetzt. Das Video bleibt bei langsamen SD-Zugriffen gegebenenfalls länger auf einem Bild stehen.

## Eigene Videodatei konvertieren

Das Quellvideo selbst gehört **nicht** ins Repository. Der Konverter akzeptiert gängige Formate, sofern FFmpeg sie dekodieren kann. Die Beispielstartzeit von 90 Sekunden ist frei wählbar.

```bash
python tools/create_test_loop.py "QUELLE.mp4" --start 00:01:30 --seconds 120 --output TEST.LOOP
python tools/check_loop.py TEST.LOOP
```

Für zehn Sekunden synthetisches Testmaterial genügt:

```bash
python tools/make_demo_loop.py TEST.LOOP --seconds 10
```

Das Format ist in [docs/DATEIFORMAT.md](docs/DATEIFORMAT.md) beschrieben. Eine 120-Sekunden-Datei hat 199.680.000 Byte und besteht aus 2.400 Blöcken. Audio wird derzeit übersprungen, nicht wiedergegeben. Es wird bewusst keine fremde Videodatei mitgeliefert.

## Fehleranzeige

Roter Hintergrund mit gelben Balken:

| Balken | Bedeutung |
|---:|---|
| 1 | microSD-Karte konnte nicht eingebunden werden |
| 2 | `TEST.LOOP` fehlt |
| 3 | Dateigröße passt nicht zum Blockformat |
| 4 | Fehler beim Lesen |

Der nächste Tastendruck führt zurück zur Testbildfolge.

## Bekannte Grenzen

- Kein HDMI-Ton in der Player-Firmware.
- 320 × 240 Bildinhalt; auf breiteren Monitoren hängt die Darstellung vom Skalierungsmodus des Displays ab.
- Kein Bildwechsel exakt zur HDMI-Vertikalsynchronisation: unter Umständen horizontale Übergangsartefakte.
- Kein automatisches Erkennen von HDMI-Steckerentfernung; solange USB-Strom anliegt, bleibt das Board eingeschaltet.
- Strommessung unter kontinuierlicher SD-Karten-Last und Prüfung kurzer Lastspitzen stehen noch aus.

## Herkunft und Lizenz

Das Projekt verwendet Teile aus [FRANK MICRO](https://github.com/rh1tech/frank-micro), [FRANK HDMI Audio](https://github.com/rh1tech/frank-hdmi-audio) und FatFs. Alle originalen Copyright-Vermerke und Lizenzdateien der eingebundenen Bibliotheken bleiben erhalten. Der Player-Quellcode steht unter **GPL-3.0-or-later** (siehe `LICENSE`). Bei Veröffentlichung von Firmware und Treiber-Snapshots sind die jeweiligen Drittanbieter-Lizenzen zu beachten.

## Schnellprüfung ohne Hardware

```bash
python -m unittest discover -s tests -v
```

Die GitHub-Action prüft nur Tools und Demodatei. Ein Firmware-Crossbuild wird dort nicht ausgeführt; dieser benötigt zusätzlich das Pico SDK, das ARM-Toolchain-Setup und die eingebundenen Drittanbieter-Quellen.
