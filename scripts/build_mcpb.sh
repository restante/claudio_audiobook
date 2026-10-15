#!/usr/bin/env bash
# Build the Claude Desktop extension: dist/claudio-audiobook-<version>.mcpb
# The bundle holds the source and pyproject.toml; Claude Desktop installs the dependencies with uv.
set -euo pipefail
cd "$(dirname "$0")/.."
stage=dist/mcpb
rm -rf "$stage" && mkdir -p "$stage"
cp desktop/manifest.json pyproject.toml README.md LICENSE "$stage"/
cp -R src "$stage"/src
find "$stage" -name __pycache__ -prune -exec rm -rf {} +
npx -y @anthropic-ai/mcpb validate "$stage/manifest.json"
version=$(python3 -c "import json;print(json.load(open('desktop/manifest.json'))['version'])")
npx -y @anthropic-ai/mcpb pack "$stage" "dist/claudio-audiobook-$version.mcpb"
echo "built dist/claudio-audiobook-$version.mcpb"
