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
