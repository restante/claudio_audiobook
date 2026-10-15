import asyncio
import time

import pytest

from claudio_audiobook import jobs, server, service
from claudio_audiobook.options import Options

COURSE = "# Python basics\n\n# Variables\nA variable holds a value.\n\n# Loops\nA loop repeats.\n"


def wait(job_id, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        record = jobs.status(job_id)
        if record["state"] not in ("queued", "running"):
            return record
        time.sleep(0.1)
    raise AssertionError(jobs.status(job_id))


def test_prepare_saves_markdown_as_the_editable_source(isolated):
    source, outdir, book = service.prepare(markdown=COURSE, file=None, title=None, output_dir=None)
    assert book == "Python basics" and source.read_text(encoding="utf-8") == COURSE
    assert outdir == isolated / "books" / "python-basics" and source.parent == outdir


def test_prepare_needs_exactly_one_source():
    with pytest.raises(Exception, match="either"):
        service.prepare(markdown=None, file=None, title=None, output_dir=None)
    with pytest.raises(Exception, match="either"):
        service.prepare(markdown="x", file="y", title=None, output_dir=None)


def test_a_job_runs_detached_and_finishes(isolated):
    source, outdir, book = service.prepare(markdown=COURSE, file=None, title=None, output_dir=None)
    job_id = service.start_job(source, outdir, Options(format="m4b"), book)
    record = wait(job_id)
    assert record["state"] == "done", record
    assert (outdir / "python-basics.m4b").exists()
    assert "output:" in jobs.describe(record)


def test_a_failing_job_reports_why(isolated):
    source, outdir, book = service.prepare(markdown=COURSE, file=None, title=None, output_dir=None)
    spec = {"source": str(source), "outdir": str(outdir), "book": book, "force": False}
    job_id = jobs.start({**spec, "options": {"voice": "af_heart", "speed": 9.0}})
    record = wait(job_id)
    assert record["state"] == "failed" and "speed" in record["message"]


def test_a_dead_worker_is_reported_not_left_running(isolated):
    jobs._write("dead0001", {"id": "dead0001", "state": "running", "pid": 2**22 + 12345,
                             "started": time.time()})  # fmt: skip
    assert jobs.status("dead0001")["state"] == "failed"


def test_tool_dry_run_and_validation_errors_are_text_not_exceptions():
    plan = server.make_audiobook(markdown=COURSE, dry_run=True)
    assert "2 chapters" in plan and "would be saved in" in plan
    assert server.make_audiobook(markdown=COURSE, speed=5).startswith("Error: speed")
    assert server.make_audiobook(markdown=COURSE, voice="zz_nope").startswith(
        "Error: unknown voice"
    )
    assert server.make_audiobook().startswith("Error: give either")
    assert server.audiobook_status("nope").startswith("Error")


def test_a_preview_creates_nothing_in_the_output_folder(isolated):
    server.make_audiobook(markdown=COURSE, dry_run=True)
    assert not (isolated / "books").exists()


def test_tool_starts_a_job_and_status_follows_it():
    started = server.make_audiobook(markdown=COURSE, voice="af_heart:0.6,af_sky:0.4", format="wav")
    job_id = started.split()[2].rstrip(".")
    assert wait(job_id)["state"] == "done"
    assert server.audiobook_status(job_id).startswith("done")


def test_every_documented_setting_is_a_tool_argument():
    tools = asyncio.run(server.mcp.list_tools())
    schema = next(t for t in tools if t.name == "make_audiobook").inputSchema["properties"]
    expected = (
        "markdown file title output_dir voice speed lang sentence_pause clause_pause chapter_pause "
        "trim model_variant format dry_run force"
    ).split()
    assert all(name in schema for name in expected)
    names = {t.name for t in tools}
    assert names == {"make_audiobook", "audiobook_status", "list_voices", "setup_check"}
