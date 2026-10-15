"""What the CLI and the MCP server share: turning a request into a source file and a job."""

from __future__ import annotations

import re
import tempfile
import time
from pathlib import Path

from claudio_audiobook import jobs, paths, render, text
from claudio_audiobook.options import Options


def options_from(**given) -> Options:
    """Options from the settings that were actually given; the rest come from the defaults."""
    return Options(**{k: v for k, v in given.items() if v is not None})


def prepare(
    *,
    markdown: str | None,
    file: str | None,
    title: str | None,
    output_dir: str | None,
    save: bool = True,
) -> tuple[Path, Path, str]:
    """(source file, output folder, book title). Given markdown is saved as the editable source in
    the output folder; with `save=False` (a preview) it goes to a temporary file and nothing is
    created in the output folder."""
    if bool(markdown) == bool(file):
        raise render.AudiobookError(
            "give either `markdown` (the text) or `file` (a path), not both"
        )
    if file:
        source = paths.expand(file).absolute()
        book = title or source.stem
        return source, _folder(output_dir, book), book
    book = title or _first_heading(markdown) or "audiobook"
    outdir = _folder(output_dir, book)
    if save:
        outdir.mkdir(parents=True, exist_ok=True)
        source = outdir / f"{text.slug(book)}.md"
    else:
        source = Path(tempfile.mkdtemp(prefix="claudio-audiobook-")) / f"{text.slug(book)}.md"
    source.write_text(markdown, encoding="utf-8")
    return source, outdir, book


def _folder(output_dir: str | None, book: str) -> Path:
    """The absolute output folder: the one asked for (`~`, `$HOME` expanded), else the default."""
    base = paths.expand(output_dir) if output_dir else paths.output_root() / text.slug(book)
    return base.absolute()


def _first_heading(markdown: str) -> str | None:
    match = re.search(r"^#\s+(.+?)\s*#*$", markdown, re.M)
    return match.group(1) if match else None


def start_job(source: Path, outdir: Path, opts: Options, book: str, force: bool = False) -> str:
    opts.validate()
    render.read_source(source)  # fail now, not inside the background job
    return jobs.start(
        {
            "source": str(source),
            "outdir": str(outdir),
            "book": book,
            "force": force,
            "options": opts.as_dict(),
        }  # fmt: skip
    )


def run_job(job_id: str) -> int:
    """Run a recorded job to the end (called by the detached worker process)."""
    record = jobs.read(job_id)
    if record is None:
        return 1
    spec = record["spec"]
    jobs.update(job_id, state="running", stage="starting")

    def progress(stage: str, done: int, total: int, message: str) -> None:
        jobs.update(job_id, stage=stage, done=done, total=total, message=message)

    try:
        result = render.build(
            Path(spec["source"]), Path(spec["outdir"]), Options(**spec["options"]),
            book=spec["book"], force=spec["force"], progress=progress,
        )  # fmt: skip
    except Exception as error:  # reported through the job record, never lost
        jobs.update(job_id, state="failed", message=str(error), finished=time.time())
        return 1
    output = result.packaged or result.outdir
    jobs.update(job_id, state="done", stage="done", output=str(output), note=result.note,
                message="finished", finished=time.time())  # fmt: skip
    return 0
