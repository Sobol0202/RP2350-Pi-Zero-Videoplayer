#!/usr/bin/env python3
"""Konvertiert einen frei gewaehlen Videoausschnitt in das TEST.LOOP-Format
fuer RP2350-PiZero HDMI-Player V0.3.1.

Abhaengigkeiten: Python 3.9+, ffmpeg, ffprobe.
Format je Frame: 76800 Bytes RGB332 + 6400 Bytes S16LE Stereo (32kHz).
20 fps, 320x240, kein Header. Kein HDMI-Ton in Player V0.3.1.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WIDTH, HEIGHT, FPS = 320, 240, 20
AUDIO_HZ = 32000
VIDEO_BYTES = WIDTH * HEIGHT
AUDIO_BYTES = (AUDIO_HZ // FPS) * 2 * 2
FRAME_BYTES = VIDEO_BYTES + AUDIO_BYTES


def timestamp_seconds(value: str) -> float:
    parts = value.split(":")
    if len(parts) > 3:
        raise argparse.ArgumentTypeError("Zeitformat: HH:MM:SS, MM:SS oder Sekunden")
    try:
        numbers = [float(n) for n in parts]
        if not numbers or any(n < 0 for n in numbers):
            raise ValueError
        if len(numbers) == 3:
            return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
        if len(numbers) == 2:
            return numbers[0] * 60 + numbers[1]
        return numbers[0]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Ungueltige Zeit: {value}") from e


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def inspect_media(path: Path) -> tuple[float | None, bool]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise ValueError("Eingabedatei hat keinen Videostream")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    raw_duration = data.get("format", {}).get("duration")
    duration = float(raw_duration) if raw_duration not in (None, "N/A") else None
    return duration, has_audio


def convert(source: Path, output: Path, start: float, seconds: int) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Quelldatei nicht gefunden: {source}")
    if output.resolve() == source.resolve():
        raise ValueError("Ausgabe darf nicht die Videodatei ueberschreiben")
    duration, has_audio = inspect_media(source)
    if duration is not None and duration + 0.25 < start + seconds:
        raise ValueError(f"Ausschnitt bis {start + seconds:.2f} s reicht ueber das Videoende "
                         f"({duration:.2f} s) hinaus. Bitte Startzeit oder Laenge anpassen.")
    count = seconds * FPS
    print(f"Quelle: {source}", flush=True)
    print(f"Ausschnitt: Start {start:g} s, Dauer {seconds} s", flush=True)
    print("Ziel: 320x240, 20 fps, vollflaechig (bei Bedarf mittig beschnitten)", flush=True)
    print(f"Tonspur: {'vorhanden, wird mitgespeichert' if has_audio else 'nicht vorhanden, Stille wird eingefuegt'}", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="testloop_") as dirname:
        temp = Path(dirname)
        video = temp / "video.rgb"
        audio = temp / "audio.pcm"
        filter_graph = (
            "scale=320:240:force_original_aspect_ratio=increase:flags=lanczos,"
            "crop=320:240,setsar=1,fps=20,format=rgb8"
        )
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-nostdin",
             "-ss", str(start), "-i", str(source), "-t", str(seconds),
             "-map", "0:v:0", "-an", "-vf", filter_graph,
             "-frames:v", str(count), "-f", "rawvideo", "-pix_fmt", "rgb8", str(video)])
        if has_audio:
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-nostdin",
                 "-ss", str(start), "-i", str(source), "-t", str(seconds),
                 "-map", "0:a:0", "-vn", "-af", "aresample=32000,apad",
                 "-ac", "2", "-ar", str(AUDIO_HZ),
                 "-c:a", "pcm_s16le", "-f", "s16le", str(audio)])
        expected_video = VIDEO_BYTES * count
        if video.stat().st_size != expected_video:
            raise ValueError(f"Bilddaten unvollstaendig ({video.stat().st_size} statt "
                             f"{expected_video} Bytes). Kein TEST.LOOP erzeugt.")
        if has_audio and audio.stat().st_size != AUDIO_BYTES * count:
            raise ValueError(f"Audiodaten unvollstaendig ({audio.stat().st_size} Bytes).")
        stage = output.with_name(output.name + ".partial")
        try:
            with video.open("rb") as video_f, stage.open("wb") as result:
                audio_f = audio.open("rb") if has_audio else None
                try:
                    empty = bytes(AUDIO_BYTES)
                    for i in range(count):
                        frame = video_f.read(VIDEO_BYTES)
                        samples = audio_f.read(AUDIO_BYTES) if audio_f else empty
                        if len(frame) != VIDEO_BYTES or len(samples) != AUDIO_BYTES:
                            raise ValueError(f"Unvollstaendiger Datenblock: {i}")
                        result.write(frame)
                        result.write(samples)
                finally:
                    if audio_f:
                        audio_f.close()
            if stage.stat().st_size != count * FRAME_BYTES:
                raise ValueError("Falsche Gesamtdatenmenge")
            stage.replace(output)
        finally:
            stage.unlink(missing_ok=True)
    print(f"FERTIG: {output}", flush=True)
    print(f"Frames: {count} | Dauer: {seconds} s | Groesse: {output.stat().st_size:,} Bytes", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Eingabevideo, z.B. 'QUELLE.mp4'")
    parser.add_argument("--start", type=timestamp_seconds, default=0.0,
                        help="Beginn im Quellvideo; z.B. 00:01:30 (Standard: 0)")
    parser.add_argument("--seconds", type=int, default=120,
                        help="Laenge in Sekunden (Standard: 120)")
    parser.add_argument("--output", type=Path, default=Path("TEST.LOOP"),
                        help="Ausgabedatei (Standard: TEST.LOOP)")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error("--seconds muss zwischen 1 und 3600 liegen")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            parser.error(f"{binary} ist nicht im PATH")
    try:
        convert(args.video, args.output, args.start, args.seconds)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
