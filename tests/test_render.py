import wave

import pytest

from claudio_audiobook import package, render
from claudio_audiobook.options import Options

BOOK = "Intro words here.\n\n# One\nFirst chapter text.\n\n# Two\nSecond chapter text.\n"


def book(tmp_path, text=BOOK, name="book.md"):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


def wavs(out):
    return sorted(p.name for p in out.glob("*.wav"))


def test_build_writes_one_wav_per_chapter(tmp_path):
    out = tmp_path / "out"
    result = render.build(book(tmp_path), out, Options(format="wav"))
    assert wavs(out) == ["01-introduction.wav", "02-one.wav", "03-two.wav"]
    assert result.packaged is None and not list(out.glob("*.part"))
    with wave.open(str(out / "02-one.wav")) as w:
        assert w.getnchannels() == 1 and w.getframerate() == 24000


def test_resume_skips_done_chapters_and_a_changed_setting_redoes_them(tmp_path):
    out, src = tmp_path / "out", book(tmp_path)
    render.build(src, out, Options(format="wav"))
    mtime = (out / "02-one.wav").stat().st_mtime_ns
    steps = []
    render.build(src, out, Options(format="wav"), progress=lambda *a: steps.append(a[3]))
    assert any("already done" in s for s in steps)
    assert (out / "02-one.wav").stat().st_mtime_ns == mtime
    render.build(src, out, Options(format="wav", speed=1.3))
    assert (out / "02-one.wav").stat().st_mtime_ns != mtime


def test_chapter_pause_adds_silence_between_chapters_but_not_after_the_last(tmp_path):
    def seconds(name, pause):
        out = tmp_path / f"o{pause}"
        render.build(book(tmp_path), out, Options(format="wav", chapter_pause=pause))
        return package.wav_seconds(out / name)

    assert seconds("02-one.wav", 3) - seconds("02-one.wav", 0) == pytest.approx(3, abs=0.05)
    assert seconds("03-two.wav", 3) == pytest.approx(seconds("03-two.wav", 0), abs=0.01)


def test_chapters_removed_from_the_text_disappear_from_the_folder(tmp_path):
    out, src = tmp_path / "out", book(tmp_path)
    render.build(src, out, Options(format="wav"))
    src.write_text("# Only\nOne chapter.\n", encoding="utf-8")
    render.build(src, out, Options(format="wav"))
    assert wavs(out) == ["01-only.wav"]


def test_plan_text_and_errors(tmp_path):
    plan = render.plan_text(book(tmp_path), tmp_path / "o", Options())
    assert "3 chapters" in plan
    with pytest.raises(render.AudiobookError, match="no text"):
        render.read_source(book(tmp_path, "  \n", "e.md"))
    with pytest.raises(render.AudiobookError, match="not found"):
        render.read_source(tmp_path / "nope.txt")


def test_m4b_uses_the_bundled_ffmpeg_and_has_chapter_marks(tmp_path):
    out = tmp_path / "out"
    result = render.build(book(tmp_path), out, Options(format="m4b"), book="My Book")
    assert result.packaged == out / "my-book.m4b" and result.packaged.stat().st_size > 0
    assert not [p for p in out.iterdir() if p.name.startswith(".concat")]
    import subprocess

    probe = subprocess.run(
        [package.ffmpeg_exe(), "-i", str(result.packaged)], capture_output=True, text=True
    )
    assert probe.stderr.count("Chapter #") == 3 and "Introduction" in probe.stderr


def test_ffmpeg_failure_keeps_the_wavs_and_says_so(tmp_path, monkeypatch):
    def boom():
        raise package.PackageError("no ffmpeg")

    monkeypatch.setattr(package, "ffmpeg_exe", boom)
    result = render.build(book(tmp_path), tmp_path / "o", Options(format="mp3"))
    assert result.packaged is None and "WAV files are ready" in result.note


def test_ffmetadata_marks_and_escapes():
    meta = package.ffmetadata(["A", "B=1"], [1.5, 2.0], "Book")
    assert "title=Book" in meta
    assert "START=0\nEND=1500\ntitle=A" in meta and "START=1500\nEND=3500\ntitle=B\\=1" in meta
