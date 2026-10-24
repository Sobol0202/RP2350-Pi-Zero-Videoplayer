#!/usr/bin/env python3
"""Exportiert die fuer den Player benoetigten Dateien aus einem FRANK-Klon.

Unterstuetzt den lokal bereits erfolgreich angepassten FRANK-Stand.
Der Export enthaelt weder Git-Metadaten noch absolute lokale Pfade.
Original-Lizenztexte und Kommentare werden unveraendert beibehalten.
"""
import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "third_party" / "frank-micro"
NEEDED = (
    "frank-hdmi-sound/src",
    "drivers/fatfs",
    "drivers/sdcard",
    "src/boards/waveshare_rp2350_pizero.h",
)
OPTIONAL = ("LICENSE", "frank-hdmi-sound/LICENSE")


def git_head(directory: Path) -> str | None:
    p = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def apply_hdmi_fix(module: Path) -> None:
    serialiser = module / "frank_serialiser.c"
    pio = module / "frank_serialiser.pio"
    c = serialiser.read_text(encoding="utf-8")
    marker = "void dvi_serialiser_init(struct dvi_serialiser_cfg *cfg) {"
    fix = """
#if defined(PLATFORM_Z0)
    if (pio_set_gpio_base(cfg->pio, 16) != PICO_OK) {
        panic("PIO GPIO base configuration failed");
    }
#endif"""
    if "pio_set_gpio_base(cfg->pio, 16)" not in c:
        if c.count(marker) != 1:
            raise RuntimeError("HDMI serialiser API geaendert; Patch nicht angewendet")
        c = c.replace(marker, marker + fix, 1)
        serialiser.write_text(c, encoding="utf-8")
    p = pio.read_text(encoding="utf-8")
    old_a = "pio_sm_set_pins_with_mask(pio, sm, 2u << data_pins, 3u << data_pins);"
    old_b = "pio_sm_set_pindirs_with_mask(pio, sm, ~0u, 3u << data_pins);"
    new_a = "pio_sm_set_pins_with_mask64(pio, sm, 2ull << data_pins, 3ull << data_pins);"
    new_b = "pio_sm_set_pindirs_with_mask64(pio, sm, 3ull << data_pins, 3ull << data_pins);"
    if new_a not in p:
        if p.count(old_a) != 1:
            raise RuntimeError("PIO-Pininitialisierung geaendert; Patch nicht angewendet")
        p = p.replace(old_a, new_a, 1)
    if new_b not in p:
        if p.count(old_b) != 1:
            raise RuntimeError("PIO-Pinrichtung geaendert; Patch nicht angewendet")
        p = p.replace(old_b, new_b, 1)
    pio.write_text(p, encoding="utf-8")
    if "pio_set_gpio_base(cfg->pio, 16)" not in serialiser.read_text() or new_a not in pio.read_text():
        raise RuntimeError("HDMI-Z0-Korrekturen konnten nicht validiert werden")


def export(source: Path):
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Quellverzeichnis nicht vorhanden: {source}")
    if source == DEST.resolve():
        raise SystemExit("Quelle und Ziel muessen verschieden sein")
    for rel in NEEDED:
        if not (source / rel).exists():
            raise SystemExit(f"Abhaengigkeit fehlt: {rel}; Git-Submodule initialisieren")
    # Erst in temporaeres Verzeichnis exportieren; Fehler veraendern den Bestand nicht.
    stage = ROOT / "third_party" / "frank-micro.tmp"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        for rel in (*NEEDED, *OPTIONAL):
            src, dest = source / rel, stage / rel
            if not src.exists():
                if rel in NEEDED:
                    raise RuntimeError(f"Fehlende Datei: {rel}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "build", "*.o", "*.obj"))
            else:
                shutil.copy2(src, dest)
        apply_hdmi_fix(stage / "frank-hdmi-sound/src")
        main_rev = git_head(source)
        hdmi_rev = git_head(source / "frank-hdmi-sound")
        # Keine Ursprungsverzeichnisse oder Rechnernamen in den Metadaten.
        notes = [
            "# Eingebundene FRANK-Quellen",
            "",
            "Aus einem lokalen FRANK-MICRO-Klon exportierter Treiber-Snapshot.",
            "Enthalten: HDMI-Bibliothek, SD-Karten-Treiber, FatFs und Board-Header.",
            "Die fuer RP2350-PiZero benoetigten PIO-Korrekturen sind enthalten.",
            "",
            "Upstream: https://github.com/rh1tech/frank-micro",
            "HDMI: https://github.com/rh1tech/frank-hdmi-audio",
            f"FRANK Commit: `{main_rev or 'nicht ermittelbar'}`",
            f"HDMI Commit: `{hdmi_rev or 'nicht ermittelbar'}`",
            "",
            "Die zugehoerigen Upstream-Lizenzdateien beachten.",
            "",
        ]
        (stage / "SOURCE.md").write_text("\n".join(notes), encoding="utf-8")
        if DEST.exists():
            shutil.rmtree(DEST)
        stage.rename(DEST)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    print("FRANK-Treiber exportiert:", DEST)
    print("Git-Repository enthaelt jetzt die fuer dieses Projekt benoetigten Quellen.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Pfad zum bereits funktionierenden FRANK-Klon")
    args = parser.parse_args()
    export(args.source)

if __name__ == "__main__":
    main()
