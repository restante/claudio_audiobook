"""Fetch and verify the Kokoro model files (downloaded on first use)."""

from __future__ import annotations

import hashlib
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from claudio_audiobook import paths
from claudio_audiobook.paths import model_dir

RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
Progress = Callable[[str, int], None]  # (file name, percent)


@dataclass(frozen=True)
class ModelFile:
    name: str
    sha256: str
    size: int

    @property
    def url(self) -> str:
        return f"{RELEASE}/{self.name}"


FULL = ModelFile(
    "kokoro-v1.0.onnx",
    "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    325_532_387,
)
LITE = ModelFile(
    "kokoro-v1.0.int8.onnx",
    "6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb",
    92_361_271,
)
VOICES = ModelFile(
    "voices-v1.0.bin",
    "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    28_214_398,
)
VARIANTS = {"full": FULL, "lite": LITE}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verified(path: Path, spec: ModelFile) -> bool:
    return path.is_file() and path.stat().st_size == spec.size and sha256(path) == spec.sha256


def override() -> tuple[Path, Path] | None:
    """Your own model and voices (`CLAUDIO_AUDIOBOOK_MODEL_FILE` + `CLAUDIO_AUDIOBOOK_VOICES_FILE`).

    Not checksum-verified: you picked the files, so you vouch for them.
    """
    model_path = paths.setting("MODEL_FILE")
    voices_path = paths.setting("VOICES_FILE")
    if model_path and voices_path:
        pair = (paths.expand(model_path), paths.expand(voices_path))
        if pair[0].is_file() and pair[1].is_file():
            return pair
    return None


def find(variant: str = "full") -> tuple[Path, Path] | None:
    """(model, voices) ready to use for `variant`, or None if not downloaded yet."""
    chosen = override()
    if chosen is not None:
        return chosen
    model, voices = model_dir() / VARIANTS[variant].name, model_dir() / VOICES.name
    if verified(model, VARIANTS[variant]) and verified(voices, VOICES):
        return model, voices
    return None


def voices_file() -> Path | None:
    chosen = override()
    if chosen is not None:
        return chosen[1]
    path = model_dir() / VOICES.name
    return path if verified(path, VOICES) else None


def _download(spec: ModelFile, target: Path, on_progress: Progress | None) -> None:
    part = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(spec.url, timeout=60) as response, part.open("wb") as out:
        total = int(response.headers.get("Content-Length") or spec.size)
        done, last = 0, -1
        while block := response.read(1 << 20):
            out.write(block)
            done += len(block)
            percent = done * 100 // total
            if on_progress and percent != last:
                last = percent
                on_progress(spec.name, percent)
    part.replace(target)


def ensure(
    variant: str = "full", *, voices_only: bool = False, on_progress: Progress | None = None
) -> Path:
    """Make sure the files are present and verified; returns the voices file (voices_only) or
    the model file. Downloads only what is missing."""
    if variant not in VARIANTS:
        raise ValueError(f"model must be one of {', '.join(VARIANTS)}")
    chosen = override()
    if chosen is not None:
        return chosen[1] if voices_only else chosen[0]
    model_dir().mkdir(parents=True, exist_ok=True)
    wanted = [VOICES] if voices_only else [VARIANTS[variant], VOICES]
    for spec in wanted:
        target = model_dir() / spec.name
        if verified(target, spec):
            continue
        _download(spec, target, on_progress)
        if not verified(target, spec):
            target.unlink(missing_ok=True)
            raise RuntimeError(f"{spec.name} failed its checksum; try again or report an issue")
    return model_dir() / (VOICES.name if voices_only else VARIANTS[variant].name)
