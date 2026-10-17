"""Every setting Kokoro allows, with defaults from the environment so people set them once."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from claudio_audiobook import cover, model, paths, pocket, voices

FORMATS = ("m4b", "mp3", "wav")
ENGINES = ("kokoro", "pocket")


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
    engine: str = ""  # "kokoro" (default) or "pocket" (optional, needs the pocket-tts package)
    voice: str = (
        ""  # Kokoro: one voice or a blend "af_heart:0.6,af_sky:0.4". Pocket: a name or a clip path
    )
    speed: float = 0.0  # 0.5 to 2.0, 1.0 is normal
    lang: str | None = None  # espeak code, default: the voice's own language
    sentence_pause: float = 0.25  # seconds of silence after a sentence
    clause_pause: float = 0.1  # seconds after a comma, colon or similar
    chapter_pause: float = 1.5  # seconds of silence between chapters
    trim: bool = True  # trim silence Kokoro leaves at the ends of each sentence
    model: str = ""  # "full" (best) or "lite" (smaller, faster)
    format: str = ""  # m4b (chapters), mp3 or wav
    author: str = ""  # shown by players; default from CLAUDIO_AUDIOBOOK_AUTHOR
    narrator: str = ""  # default: the Kokoro voice
    cover: str = ""  # "" or "auto" (generate), "none", or the path of a .jpg/.png
    cover_colors: str = ""  # "#top,#bottom" for the generated cover; default: from the title

    def __post_init__(self) -> None:
        self.engine = self.engine or paths.setting("ENGINE") or "kokoro"
        if self.engine == "kokoro":
            self.voice = self.voice or paths.setting("VOICE") or "af_heart"
        # Other engines: "" means the default voice of the language. The default Kokoro voice from
        # the settings is never applied to them.
        self.speed = self.speed or _env("SPEED", 1.0)
        self.model = self.model or _env("MODEL", "full")
        self.format = self.format or _env("FORMAT", "m4b")
        self.author = self.author or paths.setting("AUTHOR")

    def validate(self) -> Options:
        if self.engine not in ENGINES:
            raise OptionError(f"engine must be one of {', '.join(ENGINES)}")
        if not 0.5 <= self.speed <= 2.0:
            raise OptionError("speed must be between 0.5 and 2.0")
        for name, high in (("sentence_pause", 5), ("clause_pause", 5), ("chapter_pause", 30)):
            if not 0 <= getattr(self, name) <= high:
                raise OptionError(f"{name} must be between 0 and {high} seconds")
        if self.model not in model.VARIANTS:
            raise OptionError(f"model must be one of {', '.join(model.VARIANTS)}")
        if self.format not in FORMATS:
            raise OptionError(f"format must be one of {', '.join(FORMATS)}")
        if self.cover not in ("", "auto", "none"):
            try:
                cover.check_image(paths.expand(self.cover))
            except (ValueError, OSError) as error:
                raise OptionError(f"cover: {error}") from error
        try:
            cover.parse_colors(self.cover_colors)
        except ValueError as error:
            raise OptionError(f"cover_colors: {error}") from error
        if self.engine == "pocket":
            if self.speed != 1.0:
                raise OptionError("speed is not supported by the pocket engine (Kokoro only)")
            try:
                pocket.validate_voice(self.voice)
                pocket.language(self.lang, self.voice)
            except pocket.PocketError as error:
                raise OptionError(str(error)) from error
            return self
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
    def narrator_name(self) -> str:
        """The narrator tag: the given name, else the Kokoro voice(s) that read it."""
        if self.narrator:
            return self.narrator
        if self.engine == "pocket":
            voice = self.voice
            if not voice:
                voice = pocket.default_voice(pocket.language(self.lang, ""))
            return f"Pocket TTS ({Path(voice).stem if pocket.is_clip(voice) else voice})"
        return "Kokoro (" + ", ".join(name for name, _ in voices.parse(self.voice)) + ")"

    @property
    def cover_path(self) -> Path | None:
        """The person's own cover image, if they gave one."""
        return paths.expand(self.cover) if self.cover not in ("", "auto", "none") else None

    @property
    def spoken_lang(self) -> str:
        return self.lang or voices.language(voices.parse(self.voice)[0][0])  # Kokoro only
