"""Regressions from the first real Claude Desktop run (bug report: literal ${HOME} folder, and a
render that sat at 0/11 chapters)."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from claudio_audiobook import espeak, jobs, paths, render, server, service, text
from claudio_audiobook.options import Options

COURSE = "# One\nFirst chapter.\n\n# Two\nSecond chapter.\n"


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))  # Windows takes `~` from this
    (tmp_path / "home").mkdir()
    return tmp_path / "home"


# --- bug 1: ${HOME} and ~ must mean the real home folder


def test_default_folder_from_a_literal_home_placeholder_is_expanded(home, monkeypatch):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_OUTPUT", "${HOME}/Audiobooks")
    assert paths.output_root() == home / "Audiobooks"
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_OUTPUT", "~/Books")
    assert paths.output_root() == home / "Books"


@pytest.mark.parametrize("raw", ["", "${user_config.output_dir}"])
def test_blank_or_unfilled_settings_fall_back_to_defaults(home, monkeypatch, raw):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_OUTPUT", raw)
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_VOICE", raw)
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_SPEED", raw)
    assert paths.output_root() == home / "Audiobooks"
    opts = Options()
    assert (opts.voice, opts.speed) == ("af_heart", 1.0)


def test_output_dir_and_file_arguments_are_expanded_and_absolute(home):
    source, outdir, _ = service.prepare(
        markdown=COURSE, file=None, title="T", output_dir="${HOME}/x/y"
    )
    assert outdir == home / "x" / "y" and source.parent == outdir and "$" not in str(source)
    _, outdir2, _ = service.prepare(markdown=None, file="~/x/y/t.md", title=None, output_dir="~/z")
    assert outdir2 == home / "z"
    source3, _, _ = service.prepare(
        markdown=None, file="${HOME}/x/y/t.md", title=None, output_dir=None
    )
    assert source3 == home / "x" / "y" / "t.md"


def test_start_message_reports_the_real_absolute_path(home, monkeypatch):
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_OUTPUT", "${HOME}/Audiobooks")
    message = server.make_audiobook(markdown=COURSE, title="Bridging", format="wav")
    assert str(home / "Audiobooks" / "bridging") in message and "${" not in message


# --- bug 2a: a dead worker must not stay "running" (it was a zombie, which still has a pid)


def test_a_zombie_worker_is_reported_failed_with_its_output(isolated):
    crash = "print('boom'); raise SystemExit(1)"
    proc = subprocess.Popen([sys.executable, "-c", crash], stdout=subprocess.PIPE)
    for _ in range(100):  # wait until it has exited but is not reaped: a zombie
        if subprocess.run(["ps", "-o", "stat=", "-p", str(proc.pid)], capture_output=True,
                          text=True).stdout.strip().startswith("Z"):  # fmt: skip
            break
        time.sleep(0.05)
    jobs.log_file("zomb0001").write_text("Error processing file phontab\n", encoding="utf-8")
    jobs._write("zomb0001", {"id": "zomb0001", "state": "running", "pid": proc.pid,
                             "started": time.time(), "updated": time.time()})  # fmt: skip
    assert not jobs.alive(proc.pid)
    record = jobs.status("zomb0001")
    proc.wait()
    assert record["state"] == "failed" and "phontab" in record["message"]


def test_workers_started_by_this_process_are_reaped(isolated):
    source, outdir, book = service.prepare(markdown=COURSE, file=None, title=None, output_dir=None)
    job_id = service.start_job(source, outdir, Options(format="wav"), book)
    pid = jobs.read(job_id)["pid"]
    for _ in range(300):
        if not jobs.alive(pid):
            break
        time.sleep(0.1)
    assert not jobs.alive(pid) and pid not in jobs._children


# --- bug 2b: espeak-ng fails on a data path longer than ~160 characters


def test_a_long_espeak_data_path_is_replaced_by_a_short_copy(isolated, monkeypatch):
    long = isolated / ("d" * 120) / ("e" * 60) / "espeak-ng-data"
    long.mkdir(parents=True)
    (long / "phontab").write_bytes(b"data")
    monkeypatch.setattr(espeak, "_loader_data", lambda: long)
    chosen = espeak.data_path()
    assert chosen is not None and len(chosen) <= espeak.MAX_PATH
    assert (Path(chosen) / "phontab").read_bytes() == b"data"
    assert espeak.data_path() == chosen  # made once, reused


def test_a_short_espeak_data_path_is_left_alone(isolated, monkeypatch):
    short = isolated / "espeak-ng-data"
    short.mkdir()
    monkeypatch.setattr(espeak, "_loader_data", lambda: short)
    assert espeak.data_path() is None


def test_an_espeak_that_cannot_start_is_a_clear_error_not_a_dead_worker(isolated, monkeypatch):
    espeak._checked.clear()
    monkeypatch.setattr(espeak, "data_path", lambda: None)
    failing = subprocess.CompletedProcess([], 1, "", "Error processing file phontab")
    monkeypatch.setattr(espeak.subprocess, "run", lambda *a, **k: failing)
    with pytest.raises(espeak.EspeakError, match="cannot start.*phontab"):
        espeak.selfcheck()
    espeak._checked.clear()


def test_the_real_speech_engine_starts_from_this_environment():
    espeak._checked.clear()
    espeak.selfcheck()  # the bundled espeak-ng must work, also from a long install path


# --- progress inside a chapter, and a stall warning


def test_short_sentences_are_grouped_into_pieces():
    spoken = "Intro.\n" + "\n".join(["Three.", "Two.", "One."] * 40)
    parts = text.pieces(spoken, target=100)
    assert 1 < len(parts) < 40 and all(len(p) >= 100 for p in parts[:-1])


def test_progress_is_reported_per_part_inside_a_chapter(isolated):
    src = isolated / "b.md"
    src.write_text("# Long\n" + "\n".join(f"Sentence number {i} is here." * 8 for i in range(30)),
                   encoding="utf-8")  # fmt: skip
    seen = []
    render.build(src, isolated / "o", Options(format="wav"), progress=lambda *a: seen.append(a[3]))
    parts = [m for m in seen if "part" in m]
    total = int(parts[0].split("/")[-1])
    assert len(parts) == total > 3 and parts[0].endswith(f"part 1/{total}")


def test_a_live_worker_with_no_progress_is_flagged_as_stalled(isolated):
    now = time.time()
    record = {
        "id": "stal0001",
        "state": "running",
        "stage": "rendering",
        "started": now - 900,
        "updated": now - 400,
        "done": 0,
        "total": 11,
        "message": "Welcome: part 1/6",
    }
    assert "no progress for" in jobs.describe(record)
    record["updated"] = now - 5
    assert "no progress" not in jobs.describe(record)


# --- only the home folder is expanded in paths; other environment variables are never read


def test_paths_never_expand_arbitrary_environment_variables(home, monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN_FOR_TEST", "hunter2")
    for raw in ("/tmp/$SECRET_TOKEN_FOR_TEST/x", "/tmp/${SECRET_TOKEN_FOR_TEST}/x"):
        assert "hunter2" not in str(paths.expand(raw))
        assert paths.expand(raw).as_posix() == raw


@pytest.mark.parametrize("raw", ["~/x", "$HOME/x", "${HOME}/x"])
def test_home_forms_still_expand(home, raw):
    assert paths.expand(raw) == home / "x"
