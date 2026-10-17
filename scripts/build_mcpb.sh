#!/usr/bin/env bash
# Build the Claude Desktop extension.
#   ./scripts/build_mcpb.sh          -> dist/claudio-audiobook-<version>.mcpb         (Kokoro, small)
#   ./scripts/build_mcpb.sh pocket   -> dist/claudio-audiobook-pocket-<version>.mcpb  (adds Pocket TTS)
# The bundle holds the source and pyproject.toml; Claude Desktop installs the dependencies with uv.
# The Pocket bundle's pyproject gets one extra dependency (pocket-tts, which pulls in PyTorch: about 1 GB
# on first launch); the repository's own pyproject.toml and uv.lock are never changed.
set -euo pipefail
cd "$(dirname "$0")/.."
variant="${1:-default}"
stage=dist/mcpb
rm -rf "$stage" && mkdir -p "$stage"
cp pyproject.toml README.md LICENSE "$stage"/
cp -R src "$stage"/src
find "$stage" -name __pycache__ -prune -exec rm -rf {} +

if [ "$variant" = "pocket" ]; then
  python3 - "$stage" <<'PY'
import json, sys
stage = sys.argv[1]
m = json.load(open("desktop/manifest.json"))
m["name"] = "claudio-audiobook-pocket"
m["display_name"] = "claudio-audiobook (with Pocket TTS)"
m["description"] = (
    "Create audiobooks with local voices, with the optional Pocket TTS engine (7 languages, voice cloning) "
    "bundled. Install this one OR claudio-audiobook, not both. Nothing leaves your computer."
)
m["long_description"] = (
    "Same as claudio-audiobook, plus the optional Pocket TTS engine: English, Italian, French, German, "
    "Portuguese, Spanish and Dutch, 27 voices, and voice cloning from a short clip. The first launch downloads "
    "PyTorch and the voice engine (about 1 GB; under a minute on a fast connection, longer on a slow one), and "
    "Claude may show the extension as failed until that finishes: wait and reconnect. Each Pocket language model "
    "(about 400 MB) downloads once on first use. Pocket TTS weights are (c) Kyutai, CC BY 4.0. Only clone a "
    "voice you have the right to use."
)
m["server"]["mcp_config"]["env"]["CLAUDIO_AUDIOBOOK_ENGINE"] = "${user_config.engine}"
m["user_config"]["engine"] = {
    "type": "string",
    "title": "Default engine",
    "description": "pocket (7 languages, voice cloning, no speed setting) or kokoro (54 voices, speed control).",
    "default": "pocket",
    "required": False,
}
json.dump(m, open(f"{stage}/manifest.json", "w"), indent=2)
p = open(f"{stage}/pyproject.toml").read()
needle = "dependencies = ["
assert needle in p
open(f"{stage}/pyproject.toml", "w").write(p.replace(needle, needle + '\n    "pocket-tts>=3.3,<4",', 1))
PY
  out="claudio-audiobook-pocket"
else
  cp desktop/manifest.json "$stage"/
  out="claudio-audiobook"
fi

npx -y @anthropic-ai/mcpb validate "$stage/manifest.json"
version=$(python3 -c "import json;print(json.load(open('desktop/manifest.json'))['version'])")
npx -y @anthropic-ai/mcpb pack "$stage" "dist/$out-$version.mcpb"
echo "built dist/$out-$version.mcpb"
