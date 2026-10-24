#!/usr/bin/env python3
"""Erzeugt ein Repository-Archiv, inklusive lokal eingebundener Treiberquellen."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import os

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", "build", "__pycache__", ".venv", ".vscode", ".idea"}
EXCLUDE_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".wav", ".mp3", ".uf2", ".elf", ".map", ".log", ".zip"}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT.parent / "RP2350_HDMI_Testplayer_komplett.zip")
    args=parser.parse_args()
    if not (ROOT/"third_party/frank-micro/frank-hdmi-sound/src/CMakeLists.txt").exists():
        parser.error("Treiber fehlen: zuerst tools/vendor_frank.py ausfuehren")
    output=args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    count=0
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts):
                continue
            if path.suffix.lower() in EXCLUDE_EXTENSIONS: continue
            z.write(path, f"{ROOT.name}/{path.relative_to(ROOT).as_posix()}")
            count += 1
    print(f"Archiv erzeugt: {output} ({count} Dateien)")

if __name__=="__main__": main()
