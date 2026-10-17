"""The optional Pocket TTS engine: options, voices, languages, fingerprints. No model is needed."""

from __future__ import annotations

import subprocess
import sys

import pytest

from claudio_audiobook import cli, pocket, render, server
from claudio_audiobook.options import OptionError, Options

TEXT = "# One\nFirst chapter text.\n\n# Two\nSecond chapter text.\n"


def make_book(tmp_path):
    f = tmp_path / "book.md"
    f.write_text(TEXT, encoding="utf-8")
    return f


# --- Kokoro must stay exactly as it was --------------------------------------------------------


def test_kokoro_fingerprints_are_unchanged():
    """Existing audiobooks must not be re-rendered after an upgrade."""
    assert render._fingerprint("Hello there. This is a chapter.", Options()) == "eb673165379310ba"
    other = Options(voice="bf_emma", speed=0.9, lang="en-gb", trim=False)
    assert render._fingerprint("Hello there. This is a chapter.", other) == "4cf8c4e9c1d306e7"


def test_default_engine_is_kokoro_and_other_engines_change_the_fingerprint():
    assert Options().engine == "kokoro"
    kokoro = render._fingerprint("Hi.", Options())
    assert render._fingerprint("Hi.", Options(engine="pocket", voice="alba")) != kokoro


def test_engine_default_from_environment(monkeypatch):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_ENGINE", "pocket")
    assert Options().engine == "pocket"
    assert Options(engine="kokoro").engine == "kokoro"


def test_unknown_engine_is_refused():
    with pytest.raises(OptionError, match="engine must be one of"):
        Options(engine="bark").validate()


# --- voices and languages ----------------------------------------------------------------------


def test_catalogue_voices_validate_and_unknown_ones_are_refused():
    Options(engine="pocket", voice="alba").validate()
    Options(engine="pocket", voice="giovanni", lang="it").validate()
    with pytest.raises(OptionError, match="unknown pocket voice 'nobody'"):
        Options(engine="pocket", voice="nobody").validate()


def test_a_kokoro_voice_given_to_pocket_is_explained():
    with pytest.raises(OptionError, match="Kokoro voice"):
        Options(engine="pocket", voice="af_heart").validate()


def test_the_default_kokoro_voice_from_settings_is_not_applied_to_pocket(monkeypatch):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_VOICE", "af_heart")  # the Desktop default
    opts = Options(engine="pocket").validate()
    assert opts.voice == ""  # means: the default voice of the language
    assert Options().voice == "af_heart"


def test_a_cloning_file_must_exist(tmp_path):
    clip = tmp_path / "me.wav"
    clip.write_bytes(b"RIFF")
    Options(engine="pocket", voice=str(clip)).validate()
    with pytest.raises(OptionError, match="not found"):
        Options(engine="pocket", voice=str(tmp_path / "missing.wav")).validate()


def test_language_follows_lang_then_the_voice_then_english():
    assert pocket.language("it", "") == "italian"
    assert pocket.language("en-gb", "") == "english"
    assert pocket.language(None, "giovanni") == "italian"
    assert pocket.language(None, "alba") == "english"
    assert pocket.language(None, "") == "english"
    with pytest.raises(pocket.PocketError, match="Japanese|ja"):
        pocket.language("ja", "")


def test_default_voice_per_language():
    assert pocket.default_voice("italian") == "giovanni"
    assert pocket.default_voice("english") == "alba"


def test_unsupported_settings_are_refused_not_ignored():
    with pytest.raises(OptionError, match="speed"):
        Options(engine="pocket", speed=0.8).validate()
    Options(engine="pocket", speed=1.0).validate()


def test_narrator_names_the_pocket_voice():
    assert Options(engine="pocket", voice="alba").narrator_name == "Pocket TTS (alba)"
    assert Options(engine="pocket", lang="it").narrator_name == "Pocket TTS (giovanni)"


# --- building ----------------------------------------------------------------------------------


def test_a_pocket_book_builds_with_the_fake_synthesiser(tmp_path):
    out = tmp_path / "out"
    opts = Options(engine="pocket", lang="it", format="m4b")
    result = render.build(make_book(tmp_path), out, opts, book="Libro")
    assert result.packaged and result.packaged.stat().st_size > 0
    done = subprocess.run(
        [pocket_ffmpeg(), "-i", str(result.packaged)], capture_output=True, text=True
    )
    assert "composer        : Pocket TTS (giovanni)" in done.stderr
    assert done.stderr.count("Chapter #") == 2


def pocket_ffmpeg() -> str:
    from claudio_audiobook import package

    return package.ffmpeg_exe()


def test_switching_engine_redoes_the_chapters(tmp_path):
    out = tmp_path / "out"
    src = make_book(tmp_path)
    render.build(src, out, Options(format="wav"), book="B")
    stamp = (out / "01-one.wav").stat().st_mtime_ns
    render.build(src, out, Options(engine="pocket", format="wav"), book="B")
    assert (out / "01-one.wav").stat().st_mtime_ns != stamp


# --- the optional package ----------------------------------------------------------------------


def test_missing_package_gives_the_install_command(monkeypatch):
    monkeypatch.setattr(pocket, "available", lambda: False)
    with pytest.raises(pocket.PocketError) as error:
        pocket.require()
    assert "--with pocket-tts" in str(error.value) and "pip install pocket-tts" in str(error.value)


def test_a_real_build_fails_early_without_the_package(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDIO_AUDIOBOOK_FAKE")
    monkeypatch.setattr(pocket, "available", lambda: False)
    with pytest.raises(render.AudiobookError, match="pocket-tts"):
        render.build(make_book(tmp_path), tmp_path / "o", Options(engine="pocket"), book="B")
    assert not list((tmp_path / "o").glob("*.wav"))


# --- listing voices ----------------------------------------------------------------------------


def test_cli_lists_pocket_voices(capsys):
    assert cli.main(["voices", "--engine", "pocket"]) == 0
    shown = capsys.readouterr().out
    assert "giovanni" in shown and "alba" in shown and "clone" in shown.lower()


def test_mcp_lists_pocket_voices():
    assert "giovanni" in server.list_voices(engine="pocket")
    assert "af_heart" in server.list_voices()


def test_mcp_make_audiobook_accepts_the_engine(tmp_path):
    out = server.make_audiobook(markdown=TEXT, engine="pocket", lang="it", dry_run=True)
    assert "2 chapters" in out


def test_cli_main_is_importable_as_a_module():
    assert sys.modules["claudio_audiobook.cli"] is cli
