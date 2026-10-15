"""espeak-ng (the phonemizer inside Kokoro) cannot use a data folder whose path is longer than about
160 characters: it prints "Error processing file '<build machine path>/phontab'" and exits the whole
process. Claude Desktop installs extensions in a very long path, so we hand it a short copy.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from claudio_audiobook import paths

MAX_PATH = 150  # measured: 155 characters works, 165 fails
_CHECK = (
    "from kokoro_onnx.tokenizer import Tokenizer\n"
    "from kokoro_onnx.config import EspeakConfig\n"
    "import sys\n"
    "t = Tokenizer(EspeakConfig(data_path=sys.argv[1] or None))\n"
    "assert t.phonemize('Hello there.', 'en-gb')\n"
)
_checked: dict[str, tuple[bool, str]] = {}


class EspeakError(RuntimeError):
    """espeak-ng cannot start; the message says why and what to do."""


def _loader_data() -> Path:
    import espeakng_loader

    return Path(espeakng_loader.get_data_path())


def data_path() -> str | None:
    """The espeak data folder to use: the loader's own when its path is short enough (None = let
    Kokoro choose), else a copy under a short path, made once."""
    source = _loader_data()
    if len(str(source)) <= MAX_PATH:
        return None
    for base in (paths.data_dir(), Path(tempfile.gettempdir()) / "claudio-audiobook"):
        target = base / "espeak-ng-data"
        if len(str(target)) > MAX_PATH:
            continue
        marker = target / ".complete"
        if not marker.exists():
            tmp = target.with_name(target.name + ".part")
            shutil.rmtree(tmp, ignore_errors=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, tmp)
            shutil.rmtree(target, ignore_errors=True)
            tmp.rename(target)
            marker.write_text("ok", encoding="utf-8")
        return str(target)
    raise EspeakError(
        "the espeak data folder path is too long and no short place to copy it was found; "
        "set CLAUDIO_AUDIOBOOK_HOME to a short folder such as ~/.audiobook"
    )


def selfcheck() -> None:
    """Phonemize one sentence in a throwaway process, so a hard exit inside espeak-ng becomes an
    error message instead of a silently dead background worker."""
    path = data_path()
    key = path or ""
    if key not in _checked:
        try:
            done = subprocess.run(
                [sys.executable, "-c", _CHECK, key], capture_output=True, text=True, timeout=120
            )
            detail = (done.stderr or done.stdout).strip().splitlines()
            _checked[key] = (done.returncode == 0, detail[-1] if detail else "")
        except subprocess.TimeoutExpired:
            _checked[key] = (False, "espeak-ng did not answer within 120 seconds")
    ok, detail = _checked[key]
    if not ok:
        raise EspeakError(
            f"the speech engine (espeak-ng) cannot start: {detail or 'unknown error'}"
        )
