"""Where claudio-audiobook keeps its files, per operating system."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_HOME_FORM = re.compile(
    r"^(\$\{(HOME|USERPROFILE)\}|\$(HOME|USERPROFILE)(?=[/\\]|$)|%(HOME|USERPROFILE)%)"
)


def expand(value: str | Path) -> Path:
    """`~`, `$HOME` and `${HOME}` (and the Windows forms) expanded. Claude Desktop passes a manifest
    default through literally, and people type `~/Audiobooks`; both must mean the real home folder.
    No other environment variable is ever expanded, so a path can never read a secret from the
    environment (`os.path.expandvars` would)."""
    text = os.path.expanduser(str(value))
    return Path(_HOME_FORM.sub(lambda _: str(Path.home()), text))


def setting(name: str, default: str = "") -> str:
    """A `CLAUDIO_AUDIOBOOK_<name>` environment value, or `default` when it is unset, empty or an
    unfilled `${user_config.…}` placeholder (Desktop leaves those in when a field is blank)."""
    raw = os.environ.get(f"CLAUDIO_AUDIOBOOK_{name}", "").strip()
    return default if not raw or "${user_config." in raw else raw


def data_dir() -> Path:
    """Models and job records. `CLAUDIO_AUDIOBOOK_HOME` overrides it."""
    override = setting("HOME")
    if override:
        return expand(override)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "claudio-audiobook"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "claudio-audiobook"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "claudio-audiobook"


def model_dir() -> Path:
    return data_dir() / "models"


def jobs_dir() -> Path:
    path = data_dir() / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_root() -> Path:
    """Where finished audiobooks go unless a folder is given (`CLAUDIO_AUDIOBOOK_OUTPUT`)."""
    override = setting("OUTPUT")
    return expand(override) if override else Path.home() / "Audiobooks"
