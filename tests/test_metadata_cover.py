"""Audiobook tags and cover art: what players need to file an m4b under Audiobooks with a cover."""

from __future__ import annotations

import subprocess

import pytest
from PIL import Image

from claudio_audiobook import cover, package, render
from claudio_audiobook.options import OptionError, Options

BOOK = "# One\nFirst chapter text.\n\n# Two\nSecond chapter text.\n"


def make_book(tmp_path):
    f = tmp_path / "book.md"
    f.write_text(BOOK, encoding="utf-8")
    return f


def probe(path) -> str:
    done = subprocess.run([package.ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True)
    return done.stderr


# --- cover generation -------------------------------------------------------------------------


def test_generated_cover_is_a_square_jpeg(tmp_path):
    out = cover.generate(tmp_path / "c.jpg", "Python for Beginners", "Ada Lovelace", None)
    with Image.open(out) as img:
        assert img.format == "JPEG" and img.size == (1400, 1400)


def test_very_long_title_still_fits(tmp_path):
    title = "An Extremely Long Title " * 12
    out = cover.generate(tmp_path / "c.jpg", title, "A. Writer", None)
    assert out.stat().st_size > 0


def test_same_title_same_colours_and_different_title_differs():
    assert cover.default_colors("Book A") == cover.default_colors("Book A")
    assert cover.default_colors("Book A") != cover.default_colors("Book B")


def test_parse_colors():
    assert cover.parse_colors("") is None
    assert cover.parse_colors("#102030,#405060") == ((16, 32, 48), (64, 80, 96))
    one, two = cover.parse_colors("#336699")
    assert one == (51, 102, 153) and two != one  # a single colour gets a darker partner
    for bad in ("red,blue", "#12345,#abcdef", "#gggggg", "#111111,#222222,#333333"):
        with pytest.raises(ValueError):
            cover.parse_colors(bad)


def test_non_latin_title_does_not_crash(tmp_path):
    cover.generate(tmp_path / "c.jpg", "日本語の本", "著者", None)


# --- options ----------------------------------------------------------------------------------


def test_options_validate_cover_and_colours(tmp_path):
    Options(cover="none").validate()
    Options(cover="auto", cover_colors="#102030,#405060").validate()
    with pytest.raises(OptionError, match="cover"):
        Options(cover=str(tmp_path / "missing.png")).validate()
    with pytest.raises(OptionError, match="cover_colors"):
        Options(cover_colors="red").validate()
    note = tmp_path / "x.txt"
    note.write_text("not an image")
    with pytest.raises(OptionError, match="cover"):
        Options(cover=str(note)).validate()


def test_author_default_from_environment(monkeypatch):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_AUTHOR", "Claudio R.")
    assert Options().author == "Claudio R."
    assert Options(author="Other").author == "Other"


def test_narrator_defaults_to_the_voice():
    assert Options(voice="bf_emma").narrator_name == "Kokoro (bf_emma)"
    assert Options(voice="af_heart:0.6,af_sky:0.4").narrator_name == "Kokoro (af_heart, af_sky)"
    assert Options(narrator="Someone").narrator_name == "Someone"


# --- packaging --------------------------------------------------------------------------------


def test_m4b_carries_audiobook_tags_and_cover(tmp_path):
    out = tmp_path / "out"
    opts = Options(format="m4b", author="Ada Lovelace", narrator="Emma", voice="bf_emma")
    result = render.build(make_book(tmp_path), out, opts, book="My Book")
    info = probe(result.packaged)
    assert "title           : My Book" in info
    assert "artist          : Ada Lovelace" in info
    assert "album           : My Book" in info
    assert "composer        : Emma" in info
    assert "genre           : Audiobook" in info
    assert "media_type      : 2" in info
    assert "Video: mjpeg" in info and "attached pic" in info
    assert info.count("Chapter #") == 2
    assert (out / "cover.generated.jpg").exists()
    assert not (out / ".cover-embed.jpg").exists()  # temp files are cleaned up


def test_cover_none_embeds_no_picture(tmp_path):
    result = render.build(
        make_book(tmp_path), tmp_path / "o", Options(format="m4b", cover="none"), book="B"
    )
    assert "Video:" not in probe(result.packaged)
    assert not (tmp_path / "o" / "cover.generated.jpg").exists()


def test_own_png_cover_is_embedded_as_jpeg(tmp_path):
    png = tmp_path / "mine.png"
    Image.new("RGBA", (900, 1200), (200, 30, 30, 255)).save(png)
    result = render.build(
        make_book(tmp_path), tmp_path / "o", Options(format="m4b", cover=str(png)), book="B"
    )
    assert "Video: mjpeg" in probe(result.packaged)
    assert not (tmp_path / "o" / "cover.generated.jpg").exists()
    assert png.exists()  # the user's file is never modified or removed


def test_cover_dropped_in_the_folder_wins_over_the_generated_one(tmp_path):
    out = tmp_path / "o"
    out.mkdir()
    Image.new("RGB", (700, 700), (10, 120, 10)).save(out / "cover.png")
    render.build(make_book(tmp_path), out, Options(format="m4b"), book="B")
    assert not (out / "cover.generated.jpg").exists()


def test_mp3_gets_tags_and_cover(tmp_path):
    result = render.build(
        make_book(tmp_path), tmp_path / "o", Options(format="mp3", author="Ada"), book="B"
    )
    info = probe(result.packaged)
    assert "artist          : Ada" in info and "genre           : Audiobook" in info
    assert "Video: mjpeg" in info


def test_cover_and_tags_never_force_a_rerender(tmp_path):
    out = tmp_path / "o"
    src = make_book(tmp_path)
    render.build(src, out, Options(format="m4b"), book="B")
    stamp = (out / "01-one.wav").stat().st_mtime_ns
    render.build(
        src, out, Options(format="m4b", author="New", cover_colors="#111111,#999999"), book="B"
    )
    assert (out / "01-one.wav").stat().st_mtime_ns == stamp


def test_wav_format_still_saves_no_package(tmp_path):
    result = render.build(make_book(tmp_path), tmp_path / "o", Options(format="wav"), book="B")
    assert result.packaged is None
