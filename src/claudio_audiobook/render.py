"""Chapters to audio: render each chapter to a WAV (resumable), then optionally package."""

from __future__ import annotations

import hashlib
import json
import os
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from claudio_audiobook import cover, model, package, pocket, text, voices
from claudio_audiobook.options import Options
from claudio_audiobook.synth import SAMPLE_RATE, create_synth

Progress = Callable[[str, int, int, str], None]  # (stage, done, total, message)


class AudiobookError(Exception):
    """A problem the person can fix (bad file, empty text); the message says how."""


@dataclass
class Result:
    outdir: Path
    wavs: list[Path]
    packaged: Path | None
    note: str = ""


def read_source(source: Path) -> tuple[list[text.Chapter], bool]:
    try:
        raw = source.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise AudiobookError(f"file not found: {source}") from error
    except (UnicodeDecodeError, OSError) as error:
        raise AudiobookError(f"cannot read {source} as UTF-8 text: {error}") from error
    chapters = text.split_chapters(raw)
    if not chapters:
        raise AudiobookError(f"{source} has no text to read")
    return chapters, source.suffix.lower() in text.MARKDOWN_SUFFIXES


def chapter_path(outdir: Path, index: int, chapter: text.Chapter) -> Path:
    return outdir / f"{index:02d}-{text.slug(chapter.title)}.wav"


def estimate(chapters: list[text.Chapter], is_md: bool, opts: Options) -> list[float]:
    """Rough seconds of audio per chapter, including the pause after it."""
    return [
        len(c.spoken(is_md)) / text.CHARS_PER_SECOND / opts.speed + opts.chapter_pause
        for c in chapters
    ]


def plan_text(source: Path, outdir: Path, opts: Options) -> str:
    chapters, is_md = read_source(source)
    seconds = estimate(chapters, is_md, opts)
    lines = [
        f"{i:>3}  {chapter_path(outdir, i, c).name:<46} ~{s / 60:5.1f} min"
        for i, (c, s) in enumerate(zip(chapters, seconds, strict=True), 1)
    ]
    lines.append(f"{len(chapters)} chapters, about {sum(seconds) / 3600:.1f} h of audio")
    return "\n".join(lines)


def _fingerprint(spoken: str, opts: Options) -> str:
    """Changes when the text or any setting that alters the sound changes."""
    keys = (
        "voice",
        "speed",
        "lang",
        "sentence_pause",
        "clause_pause",
        "chapter_pause",
        "trim",
        "model",
    )
    parts = [spoken] + [opts.as_dict()[k] for k in keys]
    if opts.engine != "kokoro":  # Kokoro fingerprints stay as they were, so nothing re-renders
        parts.append(opts.engine)
    blob = json.dumps(parts, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def write_wav(path: Path, samples, rate: int) -> None:
    """16-bit mono WAV via a .part file, so a half-written chapter is never taken as finished."""
    import numpy as np

    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    part = path.with_name(path.name + ".part")
    with wave.open(str(part), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    os.replace(part, path)


def _render_chapter(synth, chapter, spoken, opts, index, total, say):
    """Render a chapter piece by piece (reporting each), with a sentence pause between pieces."""
    import numpy as np

    parts = text.pieces(spoken)
    chunks, rate = [], 24000
    for n, piece in enumerate(parts, 1):
        say("rendering", index - 1, total, f"{chapter.title}: part {n}/{len(parts)}")
        samples, rate = synth.render(piece, opts)
        chunks.append(samples)
        if n < len(parts) and opts.sentence_pause:
            chunks.append(np.zeros(int(opts.sentence_pause * rate), "float32"))
    return np.concatenate(chunks), rate


def _cover_for(outdir: Path, title: str, opts: Options) -> Path | None:
    """The picture to embed, or None. The person's own image wins, then one dropped in the book's
    folder (cover.jpg / cover.png), else a generated title cover (kept as cover.generated.jpg)."""
    if opts.cover == "none":
        return None
    own = opts.cover_path or cover.dropped_in(outdir)
    if own:
        return cover.normalise(own, outdir / cover.EMBED)
    try:
        colors = cover.parse_colors(opts.cover_colors)
        return cover.generate(outdir / cover.GENERATED, title, opts.author, colors)
    except (OSError, ValueError):  # a book without a cover beats no book
        return None


def build(
    source: Path,
    outdir: Path,
    opts: Options,
    *,
    book: str = "",
    force: bool = False,
    progress: Progress | None = None,
) -> Result:
    """Render `source` to `outdir`. Chapters already rendered with the same text and settings are
    skipped, so an interrupted run resumes and a changed setting redoes only what it must."""
    say = progress or (lambda *_: None)
    opts.validate()
    chapters, is_md = read_source(source)
    outdir.mkdir(parents=True, exist_ok=True)

    if opts.engine == "pocket" and not voices.fake():
        try:
            pocket.require()
        except pocket.PocketError as error:
            raise AudiobookError(str(error)) from error
    if opts.engine == "kokoro" and not voices.fake() and model.find(opts.model) is None:
        say("downloading", 0, 1, "downloading the Kokoro voice model (first use only)")
        model.ensure(
            opts.model, on_progress=lambda name, pct: say("downloading", pct, 100, f"{name} {pct}%")
        )

    state_file = outdir / ".state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    synth, wavs = create_synth(opts), []
    total = len(chapters)
    for i, chapter in enumerate(chapters, 1):
        path = chapter_path(outdir, i, chapter)
        wavs.append(path)
        spoken = chapter.spoken(is_md)
        key = _fingerprint(spoken, opts)
        if path.exists() and not force and state.get(path.name) == key:
            say("rendering", i, total, f"{chapter.title}: already done")
            continue
        samples, rate = _render_chapter(synth, chapter, spoken, opts, i, total, say)
        if i < total and opts.chapter_pause:
            import numpy as np

            samples = np.concatenate([samples, np.zeros(int(opts.chapter_pause * rate), "float32")])
        write_wav(path, samples, rate)
        state[path.name] = key
        state_file.write_text(json.dumps(state), encoding="utf-8")
        say("rendering", i, total, f"{chapter.title}: done")
    for stale in outdir.glob("[0-9][0-9]-*.wav"):  # chapters from an earlier, longer version
        if stale not in wavs:
            stale.unlink()

    if opts.format == "wav":
        return Result(outdir, wavs, None)
    say("packaging", 0, 1, f"packing {opts.format}")
    title = book or source.stem
    embed = None
    try:
        embed = _cover_for(outdir, title, opts)
        tags = package.Tags(title, opts.author, opts.narrator_name, embed)
        packed = package.package(
            outdir, text.slug(title), opts.format, wavs, [c.title for c in chapters], tags
        )
    except package.PackageError as error:
        return Result(outdir, wavs, None, f"{error}. The chapter WAV files are ready in {outdir}.")
    finally:
        (outdir / cover.EMBED).unlink(missing_ok=True)
    say("packaging", 1, 1, "done")
    return Result(outdir, wavs, packed)


__all__ = ["AudiobookError", "Result", "build", "plan_text", "SAMPLE_RATE"]
