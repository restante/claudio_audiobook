"""Background jobs stored on disk, so a long book survives a restart of Claude."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil

from claudio_audiobook import paths

STALL_SECONDS = 180  # a live worker with no progress for this long is reported as stalled
_children: dict[int, subprocess.Popen] = {}  # so finished workers are reaped, never left zombies


def _file(job_id: str) -> Path:
    return paths.jobs_dir() / f"{job_id}.json"


def log_file(job_id: str) -> Path:
    return paths.jobs_dir() / f"{job_id}.log"


def _write(job_id: str, record: dict) -> None:
    tmp = _file(job_id).with_suffix(".tmp")
    tmp.write_text(json.dumps(record), encoding="utf-8")
    os.replace(tmp, _file(job_id))


def read(job_id: str) -> dict | None:
    try:
        return json.loads(_file(job_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def start(spec: dict) -> str:
    """Record the job and run it in a detached process. `spec` has source, outdir, options, book."""
    job_id = uuid.uuid4().hex[:8]
    now = time.time()
    _write(job_id, {"id": job_id, "state": "queued", "started": now, "updated": now, "spec": spec,
                    "stage": "queued", "done": 0, "total": 0, "message": "starting"})  # fmt: skip
    cmd = [sys.executable, "-m", "claudio_audiobook", "run-job", job_id]
    log = open(log_file(job_id), "wb")  # the worker's own output, so a crash is never silent
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    log.close()
    _children[proc.pid] = proc
    update(job_id, pid=proc.pid)
    return job_id


def update(job_id: str, **fields) -> None:
    record = read(job_id) or {"id": job_id}
    record.update(fields, updated=time.time())
    _write(job_id, record)


def alive(pid: int | None) -> bool:
    """Is the worker really running? A finished child nobody has reaped still has a pid (a zombie),
    so look at the process state as well."""
    if not pid:
        return False
    child = _children.get(pid)
    if child is not None:
        if child.poll() is not None:
            _children.pop(pid, None)
            return False
        return True
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def log_tail(job_id: str, lines: int = 8) -> str:
    try:
        text = log_file(job_id).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-lines:])


def status(job_id: str) -> dict | None:
    """The job record. A worker that died unfinished is reported as failed, with its output."""
    record = read(job_id)
    if record and record.get("state") in ("queued", "running") and not alive(record.get("pid")):
        tail = log_tail(job_id)
        reason = (
            "the worker process stopped unexpectedly; running it again resumes where it stopped"
        )
        message = reason + (f". Its last output: {tail}" if tail else "")
        record.update(state="failed", message=message,
                      finished=time.time())  # fmt: skip
        _write(job_id, record)
    return record


def describe(record: dict) -> str:
    now = time.time()
    elapsed = int((record.get("finished") or now) - record["started"])
    lines = [f"{record['state']} ({record.get('stage', '')}), {elapsed}s elapsed"]
    if record.get("total"):
        lines.append(f"chapters done: {record.get('done', 0)}/{record['total']}")
    if record.get("message"):
        lines.append(str(record["message"]))
    quiet = int(now - record.get("updated", now))
    if record.get("state") == "running" and quiet > STALL_SECONDS:
        lines.append(
            f"warning: no progress for {quiet}s. A part normally takes under a minute; if this "
            f"persists the worker may be stuck (see {log_file(record['id'])})."
        )
    if record.get("output"):
        lines.append(f"output: {record['output']}")
    if record.get("note"):
        lines.append(str(record["note"]))
    return "\n".join(lines)
