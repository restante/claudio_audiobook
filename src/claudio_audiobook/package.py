"""Join chapter WAVs into one m4b (with chapter marks) or mp3, using a bundled ffmpeg."""

from __future__ import annotations

import re
import shutil
import subprocess
import wave
from pathlib import Path


class PackageError(RuntimeError):
    """ffmpeg is missing or failed; the chapter WAV files are always kept."""


def ffmpeg_exe() -> str:
    """The ffmpeg bundled with imageio-ffmpeg, else one on PATH."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        found = shutil.which("ffmpeg")
        if found:
            return found
    raise PackageError(
        "no ffmpeg available (the bundled one could not be loaded and none is on PATH)"
    )


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as src:
        return src.getnframes() / src.getframerate()


def ffmetadata(titles: list[str], durations: list[float], book: str = "") -> str:
    """ffmpeg metadata with one chapter per title, so players show a chapter list."""

    def esc(value: str) -> str:
        return re.sub(r"([=;#\\\n])", r"\\\1", value)

    lines = [";FFMETADATA1"]
    if book:
        lines.append(f"title={esc(book)}")
    start = 0
    for title, seconds in zip(titles, durations, strict=True):
        end = start + int(seconds * 1000)
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start}",
            f"END={end}",
            f"title={esc(title)}",
        ]
        start = end
    return "\n".join(lines) + "\n"


def package(
    outdir: Path, stem: str, fmt: str, files: list[Path], titles: list[str], book: str
) -> Path:
    listing, meta, target = (
        outdir / ".concat.txt",
        outdir / ".chapters.ffmeta",
        outdir / f"{stem}.{fmt}",
    )
    listing.write_text(
        "".join("file '{}'\n".format(f.name.replace("'", "'\\''")) for f in files), encoding="utf-8"
    )
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
    ]
    if fmt == "m4b":
        meta.write_text(ffmetadata(titles, [wav_seconds(f) for f in files], book), encoding="utf-8")
        cmd += ["-i", str(meta), "-map_metadata", "1", "-c:a", "aac", "-b:a", "64k"]
        cmd += ["-movflags", "+faststart"]
    else:
        cmd += ["-c:a", "libmp3lame", "-q:a", "4", "-metadata", f"title={book}"]
    cmd.append(str(target))
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise PackageError(f"ffmpeg failed: {(error.stderr or '').strip()[-300:]}") from error
    finally:
        listing.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
    return target
