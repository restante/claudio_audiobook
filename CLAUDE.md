# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is
`claudio-audiobook` turns text into an audiobook with local Kokoro voices. One Python package, three front
doors: the `claudio-audiobook` CLI, an MCP server (`claudio-audiobook-mcp`) for Claude Code (as a plugin:
`.claude-plugin/`, `.mcp.json`, `skills/`) and Claude Desktop (`desktop/manifest.json` -> `.mcpb`).
Independent of claudio-tts: no imports, own data folder.

## Commands
```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"   # setup
.venv/bin/pytest                                       # tests (fake synthesiser, no model needed)
.venv/bin/ruff format . && .venv/bin/ruff check .      # lint (line length 100)
claude plugin validate .                               # plugin + marketplace manifests
./scripts/build_mcpb.sh                                # dist/claudio-audiobook-<version>.mcpb
```
Tests set `CLAUDIO_AUDIOBOOK_FAKE=1` (silence of realistic length). Real runs: unset it; to reuse an existing
model without downloading set `CLAUDIO_AUDIOBOOK_MODEL_FILE` and `CLAUDIO_AUDIOBOOK_VOICES_FILE`.

## Architecture (src/claudio_audiobook/)
`text` (chapters, markdown cleaning) -> `render` (per-chapter WAV, resume via fingerprint in `.state.json`,
`.part` writes) -> `package` (m4b/mp3 via the ffmpeg bundled by imageio-ffmpeg). `synth` wraps Kokoro
(`options.Options` holds every setting; defaults from `CLAUDIO_AUDIOBOOK_*` env vars, which the Desktop
manifest's `user_config` sets). `jobs` runs a build in a detached process and keeps its state on disk, so a
restart of Claude does not lose it. `service` is what CLI and MCP share. `server` is the MCP tools; `guide`
holds the "how to write for the ear" text used by the server instructions, the `write_audiobook` prompt and
mirrored in `skills/audiobook/SKILL.md` (keep them in step).

## Rules
- Everything stays local. Never upload audio or text; the only network use is the one-time model download
  (SHA-256 verified in `model.py`).
- Draft, don't send: never push, release, publish (GitHub release, PyPI, marketplace) or post without the
  user saying so in the conversation.
- Bug fixes come with a test that fails without the fix. Conventional Commits (`feat(server): ...`).
- A new setting must reach CLI flag, MCP tool argument, `Options`, the Desktop `user_config` if it is a
  default worth setting once, and the README table, in the same change.
- Keep `mcp<2` until FastMCP -> MCPServer migration is done on purpose.
- Record user-facing changes in `CHANGELOG.md`; version in `pyproject.toml`, `__init__.py`,
  `.claude-plugin/plugin.json` and `desktop/manifest.json`.
