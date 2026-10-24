# TEST.LOOP – Rohdatenformat

Der Player verwendet einen festen Interleaving-Datenstrom ohne Header und ohne Dateisystem-Metadaten im Datenbereich. Das vereinfacht das Lesen auf dem RP2350.

| Parameter | Wert |
|---|---:|
| Videobild | 320 × 240 Pixel |
| Farbformat | RGB332, 1 Byte/Pixel |
| Bildrate | 20 Bilder/s |
| Audioblock | 32.000 Hz, 16-bit little-endian PCM, Stereo |
| Bilddaten pro Block | 76.800 Byte |
| Audiodaten pro Block | 6.400 Byte |
| Blocklänge | 83.200 Byte |
| Blöcke bei 120 s | 2.400 |
| Größe bei 120 s | 199.680.000 Byte |

Auf jeden Videoframe folgen 1.600 Stereo-Samplepaare (jeweils zwei vorzeichenbehaftete 16-bit-Werte). Der Stand V0.3.1 verwirft diese Tonblöcke; ein späterer Player kann sie für HDMI-Ton verwenden.

Pixelkodierung: `RRRGGGBB`. Die HDMI-LUT wandelt die Komponenten in 8-bit RGB um. Keine Kompression, kein Container, kein Header.

Die Dateigröße muss ein positives ganzzahliges Vielfaches von 83.200 sein. Eine zusätzliche Prüfsumme ist nicht vorgesehen. Der Wiedergabestart erfolgt mit dem ersten Block, nach dem letzten folgt wieder Block 0.

Der Konverter skaliert auf 320 × 240 und beschneidet bei abweichendem Seitenverhältnis die Überstände mittig. Die Ausgabe füllt so den 4:3-HDMI-Bildbereich; der tatsächliche Vollbildmodus eines 16:9-Displays hängt von dessen Skalierung ab.
