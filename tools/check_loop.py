#!/usr/bin/env python3
"""Prueft den Aufbau einer TEST.LOOP Datei am PC, ohne RP2350-Hardware."""
from pathlib import Path
import sys
import argparse

W, H, FPS = 320, 240, 20
VIDEO = W * H
AUDIO = 6400
STRIDE = VIDEO + AUDIO


def check(path: Path) -> tuple[int, float]:
    if not path.is_file():
        raise ValueError('Datei existiert nicht')
    size = path.stat().st_size
    if size < STRIDE:
        raise ValueError(f'Datei zu klein: {size} Bytes')
    if size % STRIDE:
        raise ValueError(f'Groesse {size} ist kein ganzzahliges Vielfaches von {STRIDE}')
    count = size // STRIDE
    with path.open('rb') as f:
        f.seek(0)
        first = f.read(VIDEO)
        audio = f.read(AUDIO)
        f.seek((count - 1) * STRIDE)
        last = f.read(VIDEO)
        last_audio = f.read(AUDIO)
        if len(first) != VIDEO or len(audio) != AUDIO or len(last) != VIDEO or len(last_audio) != AUDIO:
            raise ValueError('Eine Bild-/Audioeinheit ist unvollstaendig')
    return count, count / FPS


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file', type=Path)
    args = p.parse_args()
    try:
        count, duration = check(args.file)
    except ValueError as e:
        print('FEHLER:', e, file=sys.stderr)
        sys.exit(1)
    print(f'OK: {count} Frames | {duration:.2f} Sekunden | 20 fps | 320x240 RGB332 + 6400 Byte PCM pro Frame')
