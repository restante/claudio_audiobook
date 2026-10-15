"""Kokoro voices: listing, validation, and blending several voices into one."""

from __future__ import annotations

import os
import re
from collections import defaultdict

from claudio_audiobook import model

# First letter of a voice name is its language, second letter its gender (f/m).
LANGUAGES = {
    "a": ("en-us", "American English"),
    "b": ("en-gb", "British English"),
    "e": ("es", "Spanish"),
    "f": ("fr-fr", "French"),
    "h": ("hi", "Hindi"),
    "i": ("it", "Italian"),
    "j": ("ja", "Japanese"),
    "p": ("pt-br", "Brazilian Portuguese"),
    "z": ("cmn", "Mandarin Chinese"),
}
_NAME = re.compile(r"^[a-z]{2}_[a-z0-9]+$")
_LANG = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})*$")


class VoiceError(ValueError):
    """A voice or language the person asked for that cannot be used; the message says why."""


def fake() -> bool:
    """`CLAUDIO_AUDIOBOOK_FAKE=1`: no model, silence for audio. For tests and CI."""
    return bool(os.environ.get("CLAUDIO_AUDIOBOOK_FAKE"))


def language(voice: str) -> str:
    """The espeak language code a voice speaks (defaults to American English)."""
    return LANGUAGES.get(voice[:1], LANGUAGES["a"])[0]


def looks_valid(voice: str) -> bool:
    return bool(_NAME.match(voice)) and voice[:1] in LANGUAGES and voice[1:2] in ("f", "m")


def available() -> list[str]:
    """Every voice in the voices file, sorted. Downloads the small voices file if needed."""
    if fake():
        return ["af_heart", "af_sky", "am_adam", "bf_emma", "im_nicola"]
    import numpy as np

    path = model.voices_file() or model.ensure(voices_only=True)
    with np.load(path, allow_pickle=True) as data:
        return sorted(data.files)


def parse(spec: str) -> list[tuple[str, float]]:
    """`af_heart` -> [(af_heart, 1.0)]; `af_heart:0.6,af_sky:0.4` -> a weighted blend (weights
    are normalised, so `af_heart,af_sky` is an even mix)."""
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    if not parts:
        raise VoiceError("no voice given")
    out: list[tuple[str, float]] = []
    for part in parts:
        name, _, weight = part.partition(":")
        try:
            value = float(weight) if weight else 1.0
        except ValueError as error:
            raise VoiceError(f"bad weight in {part!r}; use name:0.6") from error
        if value <= 0:
            raise VoiceError(f"weight must be above 0 in {part!r}")
        out.append((name.strip(), value))
    total = sum(w for _, w in out)
    return [(n, w / total) for n, w in out]


def validate(spec: str) -> list[tuple[str, float]]:
    """Parse `spec` and check every name against the real voice list."""
    parsed = parse(spec)
    names = available()
    for name, _ in parsed:
        if name not in names:
            close = [n for n in names if name.split("_")[-1] in n or n[:2] == name[:2]][:5]
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            raise VoiceError(
                f"unknown voice {name!r}.{hint} List them with `claudio-audiobook voices`."
            )
    return parsed


def validate_lang(code: str) -> str:
    code = code.strip().lower()
    if not _LANG.match(code):
        raise VoiceError(f"{code!r} is not a language code like en-us, de, fr-fr, it")
    return code


def blend(parts: list[tuple[str, float]], style_of):
    """What to hand to Kokoro: the voice name, or a weighted mix of style arrays."""
    if len(parts) == 1:
        return parts[0][0]
    import numpy as np

    return sum(w * style_of(n) for n, w in parts).astype(np.float32)


def grouped(names: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for name in names:
        groups[language(name)].append(name)
    order = [code for code, _ in LANGUAGES.values()]
    return {code: groups[code] for code in order if code in groups}


def label(code: str) -> str:
    return next(text for key, text in LANGUAGES.values() if key == code)
