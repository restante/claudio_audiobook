"""Every setting Kokoro allows, with defaults from the environment so people set them once."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from claudio_audiobook import model, paths, voices

FORMATS = ("m4b", "mp3", "wav")


class OptionError(ValueError):
    """A setting outside its allowed range; the message says what is allowed."""


def _env(name: str, default):
    raw = paths.setting(name)
    if not raw:
        return default
    try:
        return type(default)(raw)
    except ValueError:
        return default


@dataclass
class Options:
    voice: str = ""  # one voice, or a blend "af_heart:0.6,af_sky:0.4"
    speed: float = 0.0  # 0.5 to 2.0, 1.0 is normal
    lang: str | None = None  # espeak code, default: the voice's own language
    sentence_pause: float = 0.25  # seconds of silence after a sentence
    clause_pause: float = 0.1  # seconds after a comma, colon or similar
    chapter_pause: float = 1.5  # seconds of silence between chapters
    trim: bool = True  # trim silence Kokoro leaves at the ends of each sentence
    model: str = ""  # "full" (best) or "lite" (smaller, faster)
    format: str = ""  # m4b (chapters), mp3 or wav

    def __post_init__(self) -> None:
        self.voice = self.voice or paths.setting("VOICE") or "af_heart"
        self.speed = self.speed or _env("SPEED", 1.0)
        self.model = self.model or _env("MODEL", "full")
        self.format = self.format or _env("FORMAT", "m4b")

    def validate(self) -> Options:
        if not 0.5 <= self.speed <= 2.0:
            raise OptionError("speed must be between 0.5 and 2.0")
        for name, high in (("sentence_pause", 5), ("clause_pause", 5), ("chapter_pause", 30)):
            if not 0 <= getattr(self, name) <= high:
                raise OptionError(f"{name} must be between 0 and {high} seconds")
        if self.model not in model.VARIANTS:
            raise OptionError(f"model must be one of {', '.join(model.VARIANTS)}")
        if self.format not in FORMATS:
            raise OptionError(f"format must be one of {', '.join(FORMATS)}")
        try:
            voices.validate(self.voice)
            if self.lang:
                self.lang = voices.validate_lang(self.lang)
        except voices.VoiceError as error:
            raise OptionError(str(error)) from error
        return self

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def spoken_lang(self) -> str:
        return self.lang or voices.language(voices.parse(self.voice)[0][0])
