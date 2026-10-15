"""The `claudio-audiobook` command line."""

from __future__ import annotations

import argparse
import shutil
import sys

from claudio_audiobook import (
    __version__,
    espeak,
    model,
    package,
    paths,
    render,
    service,
    voices,
)
from claudio_audiobook.options import FORMATS, OptionError


def _add_options(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--voice", help='one voice, or a blend: "af_heart:0.6,af_sky:0.4" (default af_heart)'
    )
    p.add_argument("--speed", type=float, help="0.5 to 2.0 (default 1.0)")
    p.add_argument(
        "--lang", help="espeak language to pronounce with, e.g. de (default: the voice's own)"
    )
    p.add_argument("--sentence-pause", type=float, help="seconds after a sentence (default 0.25)")
    p.add_argument(
        "--clause-pause", type=float, help="seconds after a comma or colon (default 0.1)"
    )
    p.add_argument("--chapter-pause", type=float, help="seconds between chapters (default 1.5)")
    p.add_argument(
        "--no-trim", action="store_true", help="keep the silence Kokoro leaves at sentence ends"
    )
    p.add_argument(
        "--model", choices=sorted(model.VARIANTS), help="full (best) or lite (smaller, faster)"
    )
    p.add_argument("--format", choices=FORMATS, help="m4b with chapter marks (default), mp3 or wav")


def _options(a: argparse.Namespace):
    return service.options_from(
        voice=a.voice, speed=a.speed, lang=a.lang, sentence_pause=a.sentence_pause,
        clause_pause=a.clause_pause, chapter_pause=a.chapter_pause,
        trim=False if a.no_trim else None, model=a.model, format=a.format,
    )  # fmt: skip


def cmd_build(a: argparse.Namespace) -> int:
    try:
        opts = _options(a).validate()
        source, outdir, book = service.prepare(
            markdown=None, file=a.file, title=a.title, output_dir=a.output
        )
        if a.dry_run:
            print(render.plan_text(source, outdir, opts))
            return 0

        def progress(stage, done, total, message):
            print(f"[{stage} {done}/{total}] {message}", file=sys.stderr, flush=True)

        result = render.build(source, outdir, opts, book=book, force=a.force, progress=progress)
    except (render.AudiobookError, OptionError, voices.VoiceError) as error:
        print(f"claudio-audiobook: {error}", file=sys.stderr)
        return 1
    if result.note:
        print(result.note, file=sys.stderr)
    print(result.packaged or result.outdir)
    return 0


def cmd_run_job(a: argparse.Namespace) -> int:
    return service.run_job(a.job_id)


def cmd_voices(a: argparse.Namespace) -> int:
    names = voices.available()
    for code, group in voices.grouped(names).items():
        print(f"{voices.label(code)} ({code}): {', '.join(group)}")
    return 0


def cmd_download_model(a: argparse.Namespace) -> int:
    def progress(name, pct):
        print(f"\r{name}: {pct}%", end="", file=sys.stderr, flush=True)

    model.ensure(a.model, on_progress=progress)
    print(f"\nready in {paths.model_dir()}")
    return 0


def cmd_doctor(a: argparse.Namespace) -> int:
    ok = True

    def check(good: bool, label: str, hint: str = "") -> None:
        nonlocal ok
        ok &= good
        print(
            f"{'ok  ' if good else 'FAIL'} {label}" + (f"  -> {hint}" if hint and not good else "")
        )

    check(True, f"claudio-audiobook {__version__}, Python {sys.version.split()[0]}")
    check(
        model.find("full") is not None,
        "Kokoro full model",
        "run `claudio-audiobook download-model`",
    )
    check(
        model.find("lite") is not None or model.find("full") is not None, "a Kokoro model is usable"
    )
    try:
        check(True, f"ffmpeg: {package.ffmpeg_exe()}")
    except package.PackageError as error:
        check(False, "ffmpeg", str(error))
    try:
        espeak.selfcheck()
        check(True, "speech engine (espeak-ng) starts")
    except espeak.EspeakError as error:
        check(False, "speech engine (espeak-ng)", str(error))
    print(f"data folder: {paths.data_dir()}\nbooks go to: {paths.output_root()}")
    print(f"system ffmpeg (not required): {shutil.which('ffmpeg') or 'none'}")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claudio-audiobook",
        description="Turn text into an audiobook with local Kokoro voices.",
    )
    parser.add_argument("--version", action="version", version=f"claudio-audiobook {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="turn a text or markdown file into an audiobook")
    p.add_argument("file")
    p.add_argument("-o", "--output", help="output folder (default: ~/Audiobooks/<title>)")
    p.add_argument("--title", help="book title (default: the file name)")
    p.add_argument("--force", action="store_true", help="redo chapters that are already done")
    p.add_argument(
        "--dry-run", action="store_true", help="show the chapters and length, write nothing"
    )
    _add_options(p)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("run-job", help=argparse.SUPPRESS)
    p.add_argument("job_id")
    p.set_defaults(func=cmd_run_job)

    p = sub.add_parser("voices", help="list the available voices")
    p.set_defaults(func=cmd_voices)

    p = sub.add_parser("download-model", help="download and verify the Kokoro model")
    p.add_argument("--model", choices=sorted(model.VARIANTS), default="full")
    p.set_defaults(func=cmd_download_model)

    p = sub.add_parser("doctor", help="check the installation")
    p.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
