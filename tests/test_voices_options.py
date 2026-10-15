import numpy as np
import pytest

from claudio_audiobook import voices
from claudio_audiobook.options import OptionError, Options


def test_parse_single_and_blend():
    assert voices.parse("af_heart") == [("af_heart", 1.0)]
    assert voices.parse("af_heart:3,af_sky:1") == [("af_heart", 0.75), ("af_sky", 0.25)]
    assert [w for _, w in voices.parse("af_heart,af_sky")] == [0.5, 0.5]


@pytest.mark.parametrize("bad", ["", "af_heart:x", "af_heart:0", "af_heart:-1"])
def test_parse_rejects_bad_specs(bad):
    with pytest.raises(voices.VoiceError):
        voices.parse(bad)


def test_unknown_voice_suggests_close_ones():
    with pytest.raises(voices.VoiceError, match="Did you mean"):
        voices.validate("af_hart")
    with pytest.raises(voices.VoiceError, match="unknown voice"):
        voices.validate("zz_nobody")


def test_blend_is_a_weighted_mix():
    styles = {"a": np.full((2,), 1.0, "float32"), "b": np.full((2,), 3.0, "float32")}
    mixed = voices.blend([("a", 0.75), ("b", 0.25)], styles.__getitem__)
    assert np.allclose(mixed, 1.5) and mixed.dtype == np.float32
    assert voices.blend([("a", 1.0)], styles.__getitem__) == "a"


def test_language_follows_the_voice_and_can_be_overridden():
    assert Options(voice="im_nicola").validate().spoken_lang == "it"
    assert Options(voice="im_nicola", lang="de").validate().spoken_lang == "de"
    with pytest.raises(OptionError):
        Options(lang="Not A Lang!").validate()


def test_defaults_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_VOICE", "bf_emma")
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_SPEED", "1.2")
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_FORMAT", "mp3")
    opts = Options()
    assert (opts.voice, opts.speed, opts.format) == ("bf_emma", 1.2, "mp3")
    assert Options(speed=0.9).speed == 0.9  # explicit beats the default


@pytest.mark.parametrize(
    "field,value",
    [
        ("speed", 3.0),
        ("sentence_pause", -1),
        ("chapter_pause", 99),
        ("model", "huge"),
        ("format", "ogg"),
    ],
)
def test_out_of_range_settings_are_clear_errors(field, value):
    with pytest.raises(OptionError):
        Options(**{field: value}).validate()
