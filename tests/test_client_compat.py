"""Tool schemas stay simple: Cursor and Gemini mishandle `anyOf [T, null]` on optional params."""

from __future__ import annotations

import json

from claudio_audiobook import server


def _schemas() -> dict[str, dict]:
    return {t.name: t.parameters for t in server.mcp._tool_manager.list_tools()}


def test_no_union_or_null_in_tool_schemas():
    for name, schema in _schemas().items():
        text = json.dumps(schema)
        assert "anyOf" not in text, name
        assert '"null"' not in text, name
        assert '"default": null' not in text, name


def test_optional_parameters_stay_optional_and_typed():
    schema = _schemas()["make_audiobook"]
    props = schema["properties"]
    assert props["voice"]["type"] == "string"
    assert props["speed"]["type"] == "number"
    assert props["trim"]["type"] == "boolean"
    assert "voice" not in schema.get("required", [])
    assert "speed" not in schema.get("required", [])


def test_none_is_still_accepted_by_the_tool():
    out = server.make_audiobook(markdown="# One\n\nHello.", dry_run=True, voice=None, speed=None)
    assert "1 chapters" in out


def test_format_guidance_reaches_the_ai():
    """The AI must default to m4b and tell the person that mp3 and wav have no chapter list."""
    from claudio_audiobook.guide import WRITING_GUIDE

    tool = next(t for t in server.mcp._tool_manager.list_tools() if t.name == "make_audiobook")
    for text in (tool.description, WRITING_GUIDE):
        low = text.lower()
        assert "m4b" in low and "default" in low
        assert "no chapter" in low


def test_skill_mirrors_the_format_guidance():
    from pathlib import Path

    skill = Path(server.__file__).parents[2] / "skills" / "audiobook" / "SKILL.md"
    low = skill.read_text(encoding="utf-8").lower()
    assert "m4b" in low and "no chapter" in low
