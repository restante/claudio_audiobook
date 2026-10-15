import pytest


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Own data and output folders, and the fake synthesiser: no model, no real audio."""
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_OUTPUT", str(tmp_path / "books"))
    monkeypatch.setenv("CLAUDIO_AUDIOBOOK_FAKE", "1")
    for name in ("VOICE", "SPEED", "MODEL", "FORMAT"):
        monkeypatch.delenv(f"CLAUDIO_AUDIOBOOK_{name}", raising=False)
    return tmp_path
