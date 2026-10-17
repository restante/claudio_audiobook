"""Pocket TTS (Kyutai): an optional second engine. Small, CPU-only, clones a voice from a clip.

The `pocket-tts` package is not a dependency of claudio-audiobook (it pulls in PyTorch). Install it
beside this one: `uv tool install claudio-audiobook --with pocket-tts`, or `pip install pocket-tts`.
Its model weights are CC BY 4.0 (Kyutai) and download once from Hugging Face on first use.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from claudio_audiobook import paths, voices
from claudio_audiobook.text import CHARS_PER_SECOND

SAMPLE_RATE = 24000
INSTALL_HINT = (
    "the pocket engine needs the pocket-tts package. Install it next to claudio-audiobook: "
    "`uv tool install claudio-audiobook --with pocket-tts` or `pip install pocket-tts`"
)
# espeak-style language prefix -> the Pocket model that speaks it
LANGUAGES = {
    "en": "english",
    "it": "italian",
    "fr": "french",
    "de": "german",
    "pt": "portuguese",
    "es": "spanish",
    "nl": "dutch",
}
# The built-in catalogue (Pocket's own list). Any voice can speak any language; these are the
# defaults, and the voices recorded in a language make that language's natural default.
DEFAULT_VOICE = {
    "english": "alba",
    "italian": "giovanni",
    "spanish": "lola",
    "german": "juergen",
    "portuguese": "rafael",
    "french": "estelle",
    "dutch": "daan",
}
CATALOGUE = (
    "alba anna azelma bill_boerst caro_davy charles cosette daan eponine estelle eve fantine "
    "george giovanni jane javert jean juergen lola marius mary michael paul peter_yearsley "
    "rafael stuart_bell vera"
).split()
_AUDIO_SUFFIXES = (".wav", ".mp3", ".flac", ".ogg")


class PocketError(RuntimeError):
    """The Pocket engine cannot be used as asked; the message says why and what to do."""


def available() -> bool:
    return importlib.util.find_spec("pocket_tts") is not None


def require() -> None:
    if not available():
        raise PocketError(INSTALL_HINT)


def language(lang: str | None, voice: str) -> str:
    """The Pocket model to use: from `lang` if given, else from a language's default voice,
    else English."""
    if lang:
        prefix = lang.split("-")[0].lower()
        if prefix not in LANGUAGES:
            raise PocketError(
                f"the pocket engine does not speak {lang!r}; it speaks "
                + ", ".join(sorted(LANGUAGES))
                + ". Use the default engine (kokoro) for other languages."
            )
        return LANGUAGES[prefix]
    for name, voice_name in DEFAULT_VOICE.items():
        if voice == voice_name:
            return name
    return "english"


def default_voice(lang_name: str) -> str:
    return DEFAULT_VOICE[lang_name]


def is_clip(spec: str) -> bool:
    """A voice given as a path to an audio clip, to clone."""
    return bool(spec) and (
        "/" in spec
        or "\\" in spec
        or spec.startswith("~")
        or spec.lower().endswith(_AUDIO_SUFFIXES)
    )


def validate_voice(spec: str) -> str:
    """The voice to use: '' (the language's default), a catalogue name, or an audio clip path."""
    if not spec:
        return spec
    if is_clip(spec):
        clip = paths.expand(spec)
        if not clip.is_file():
            raise PocketError(f"voice clip not found: {clip}")
        return spec
    if spec in CATALOGUE:
        return spec
    if voices.looks_valid(spec):
        raise PocketError(
            f"{spec!r} is a Kokoro voice. The pocket engine has its own: {', '.join(CATALOGUE)}, "
            "or give the path of a short audio clip to clone."
        )
    close = [name for name in CATALOGUE if name.startswith(spec[:2])][:5]
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    raise PocketError(
        f"unknown pocket voice {spec!r}.{hint} "
        "List them with `claudio-audiobook voices --engine pocket`."
    )


def listing() -> str:
    names = ", ".join(CATALOGUE)
    return (
        f"Pocket TTS voices: {names}\n"
        "Defaults per language: "
        + ", ".join(f"{lang} {v}" for lang, v in DEFAULT_VOICE.items())
        + "\n"
        "Any voice can speak any of the engine's languages (en, it, fr, de, pt, es, nl). "
        "To use your own voice, pass the path of a clean 5-30 second clip you may clone."
    )


class PocketSynth:
    """Loads one Pocket model per language, and one voice state per voice, once."""

    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._states: dict[tuple[str, str], object] = {}

    def _model(self, lang_name: str):
        if lang_name not in self._models:
            require()
            from pocket_tts import TTSModel

            self._models[lang_name] = TTSModel.load_model(language=lang_name)
        return self._models[lang_name]

    def render(self, text: str, opts):
        """(float32 samples, sample rate) for `text`. Silence of a realistic length in fake mode."""
        import numpy as np

        if voices.fake():
            seconds = max(0.1, len(text) / CHARS_PER_SECOND)
            return np.zeros(int(seconds * SAMPLE_RATE), dtype="float32"), SAMPLE_RATE
        lang_name = language(opts.lang, opts.voice)
        voice = opts.voice or default_voice(lang_name)
        if is_clip(voice):
            voice = str(Path(paths.expand(voice)))
        model = self._model(lang_name)
        key = (lang_name, voice)
        if key not in self._states:
            self._states[key] = model.get_state_for_audio_prompt(voice)
        audio = model.generate_audio(self._states[key], text)
        samples = audio.detach().cpu().numpy().reshape(-1).astype("float32")
        if len(samples) == 0:
            raise PocketError("Pocket TTS produced no audio for this text")
        return samples, int(model.sample_rate)
