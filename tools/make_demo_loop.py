#!/usr/bin/env python3
"""Generiert eine eigenstaendige 10-Sekunden-TEST.LOOP-Datei ohne fremdes Videomaterial.

320x240 RGB332, 20fps, pro Frame +6400 Byte stille 32-kHz-Stereo-PCM-Daten.
Standardbibliothek, kein FFmpeg erforderlich.
"""
from pathlib import Path
import argparse

W, H, FPS = 320, 240, 20
AUDIO_BYTES = 6400
PALETTE = (0xE0, 0xFC, 0x1C, 0x1F, 0x03, 0xE3, 0xFF, 0x00)


def generate(output: Path, seconds: int = 10):
    output.parent.mkdir(parents=True, exist_ok=True)
    silence = bytes(AUDIO_BYTES)
    with output.open('wb') as file:
        for index in range(FPS * seconds):
            pixels = bytearray(W * H)
            phase = (index * 3) % W
            for y in range(H):
                offset = y * W
                for x in range(W):
                    band = ((x + phase) // 40) % len(PALETTE)
                    color = PALETTE[band]
                    if 70 <= y < 95:
                        color = (x * 255 // (W - 1)) & 0xE0  # R gradient
                    if 95 <= y < 120:
                        color = ((x * 255 // (W - 1)) >> 3) & 0x1C  # G gradient
                    if 120 <= y < 145:
                        color = ((x * 255 // (W - 1)) >> 6) & 0x03  # B gradient
                    if (x + y + index) % 47 < 2:
                        color = 0xFF  # moving white diagonal stripes
                    if x in (0, W - 1) or y in (0, H - 1):
                        color = 0xFF  # edges of image
                    pixels[offset + x] = color
            # 26x26 dot travelling across the picture.
            cx = ((index * 6) % (W + 26)) - 26
            for y in range(165, 191):
                for x in range(max(0, cx), min(W, cx + 26)):
                    pixels[y * W + x] = 0x00
            file.write(pixels)
            file.write(silence)
    print(f'{output} ({output.stat().st_size:,} Bytes, {seconds}s @ {FPS}fps)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', default='TEST.LOOP', type=Path)
    parser.add_argument('--seconds', type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error('--seconds nur 1 bis 120')
    generate(args.output, args.seconds)
