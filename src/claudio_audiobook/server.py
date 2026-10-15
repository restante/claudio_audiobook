"""MCP server (stdio) for Claude Code and Claude Desktop."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from claudio_audiobook import espeak, jobs, model, package, paths, render, service, voices
from claudio_audiobook.guide import WRITING_GUIDE
from claudio_audiobook.options import OptionError

mcp = FastMCP(
    "claudio-audiobook",
    instructions="Makes audiobooks locally with Kokoro voices.\n\n" + WRITING_GUIDE,
)

_ERRORS = (render.AudiobookError, OptionError, voices.VoiceError, espeak.EspeakError)


@mcp.tool()
def make_audiobook(
    markdown: str | None = None,
    file: str | None = None,
    title: str | None = None,
    output_dir: str | None = None,
    voice: str | None = None,
    speed: float | None = None,
    lang: str | None = None,
    sentence_pause: float | None = None,
    clause_pause: float | None = None,
    chapter_pause: float | None = None,
    trim: bool | None = None,
    model_variant: str | None = None,
    format: str | None = None,
    author: str | None = None,
    narrator: str | None = None,
    cover: str | None = None,
    cover_colors: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """Turn text into an audiobook with local Kokoro voices (nothing leaves this computer).

    Give the text as `markdown` (you write it; one '# ' heading starts each chapter, and the title is
    read aloud) or the path of an existing .txt/.md as `file`. With dry_run=true it only returns the
    chapter plan and the estimated length. Otherwise it starts a background job and returns its id:
    poll audiobook_status. Settings: voice (e.g. af_heart, or a blend "af_heart:0.6,af_sky:0.4"), speed
    0.5-2.0, lang (espeak code such as de), sentence_pause / clause_pause / chapter_pause in seconds,
    trim (cut silence at sentence ends), model_variant "full" or "lite", format "m4b" (chapters),
    "mp3" or "wav". Book tags: author, narrator (default: the Kokoro voice). Cover art: by default a
    title cover is generated locally; choose its look with cover_colors "#top,#bottom" (hex, pick
    colours that suit the topic), or pass cover="path/to/image.png" (jpg/png) for your own, or
    cover="none". Unset settings use the user's defaults. force=true redoes finished chapters.
    """
    try:
        opts = service.options_from(
            voice=voice, speed=speed, lang=lang, sentence_pause=sentence_pause,
            clause_pause=clause_pause, chapter_pause=chapter_pause, trim=trim,
            model=model_variant, format=format, author=author, narrator=narrator, cover=cover,
            cover_colors=cover_colors,
        )  # fmt: skip
        opts.validate()
        source, outdir, book = service.prepare(
            markdown=markdown, file=file, title=title, output_dir=output_dir, save=not dry_run
        )
        if dry_run:
            return render.plan_text(source, outdir, opts) + f"\nwould be saved in: {outdir}"
        job_id = service.start_job(source, outdir, opts, book, force)
    except _ERRORS as error:
        return f"Error: {error}"
    return (
        f"Started job {job_id}. Output folder: {outdir} (source text: {source}). "
        "Call audiobook_status with this job_id to follow progress. The first run downloads the "
        "voice model (about 330 MB, once)."
    )


@mcp.tool()
def audiobook_status(job_id: str) -> str:
    """Progress of a make_audiobook job: state, stage, chapter progress and the output path."""
    record = jobs.status(job_id)
    if record is None:
        return "Error: unknown job id"
    return jobs.describe(record)


@mcp.tool()
def list_voices() -> str:
    """The voices available, grouped by language. A voice can also be a blend: "af_heart:0.6,af_sky:0.4"."""
    try:
        names = voices.available()
    except Exception as error:  # e.g. offline on first use
        return f"Error: could not load the voice list: {error}"
    return "\n".join(
        f"{voices.label(code)} ({code}): {', '.join(group)}"
        for code, group in voices.grouped(names).items()
    )


@mcp.tool()
def setup_check() -> str:
    """Report whether the voice model, ffmpeg and the output folder are ready."""
    try:
        ffmpeg = package.ffmpeg_exe()
    except package.PackageError as error:
        ffmpeg = f"missing ({error})"
    try:
        espeak.selfcheck()
        speech_engine = "ok"
    except espeak.EspeakError as error:
        speech_engine = f"FAILED: {error}"
    return json.dumps(
        {
            "speech_engine": speech_engine,
            "full_model_ready": model.find("full") is not None,
            "lite_model_ready": model.find("lite") is not None,
            "ffmpeg": ffmpeg,
            "audiobooks_folder": str(paths.output_root()),
            "note": "Missing models download automatically on the first audiobook.",
        },
        indent=2,
    )


@mcp.prompt()
def write_audiobook(topic: str, level: str = "beginner", length_minutes: int = 60) -> str:
    """Write a spoken-style course on a topic and turn it into an audiobook."""
    return (
        f"Create an audiobook course on: {topic}. Level: {level}. Target length: about "
        f"{length_minutes} minutes.\n\n{WRITING_GUIDE}"
    )


def _flatten_optionals() -> None:
    """Advertise `str | None` parameters as plain `string`.

    FastMCP emits `anyOf: [{type: T}, {type: null}]` with `default: null`. Cursor and Gemini reject or
    mishandle that union. The parameters are still optional (not in `required`), and the tool functions
    still accept None, so only the advertised schema changes.
    """
    for tool in mcp._tool_manager.list_tools():
        for prop in tool.parameters.get("properties", {}).values():
            branches = prop.get("anyOf")
            if not branches:
                continue
            kept = [b for b in branches if b.get("type") != "null"]
            if len(kept) == 1:
                del prop["anyOf"]
                prop.update(kept[0])
                if prop.get("default") is None:
                    prop.pop("default", None)


_flatten_optionals()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
