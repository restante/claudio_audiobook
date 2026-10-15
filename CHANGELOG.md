# Changelog

## 0.1.2

Audiobook tags and cover art, and support for other MCP clients.

- New: the m4b (and mp3) now carries what audiobook players need: title, author, narrator (composer), album,
  genre "Audiobook" and, for m4b, the audiobook media type, so Apple Books and others file it under Audiobooks.
- New: cover art. A title cover is generated locally (Pillow, no network); the AI can choose its colours
  (`cover_colors`), or you give your own `.jpg`/`.png` (`cover`), or drop a `cover.jpg` in the book's folder, or
  `cover=none`. The art is embedded in the file and kept as `cover.generated.jpg`.
- New settings `author`, `narrator`, `cover`, `cover_colors` (CLI flags, MCP arguments, Desktop setting for the
  author). Changing them only repackages the file; no chapter is rendered again.
- New dependency: `pillow`.
- Published on PyPI: `uvx --from claudio-audiobook claudio-audiobook-mcp` or `uv tool install claudio-audiobook`. The
  Claude Code plugin now runs the pinned PyPI version.
- The tool description, writing guide and skill now tell the AI to leave `format` unset (m4b, with chapters) and
  to say that mp3 and wav have no chapter list.
- New: works with other MCP clients (Cursor, VS Code / GitHub Copilot, Gemini CLI, Codex CLI). The README has
  the config for each. Tool schemas now advertise optional parameters as plain types instead of
  `anyOf [T, null]`, which Cursor and Gemini mishandle. Behaviour for Claude is unchanged.

## 0.1.1

Fixes from the first real Claude Desktop run.

- Fix: the speech engine (espeak-ng) cannot use a data folder whose path is longer than about 160 characters,
  and Desktop installs extensions in a path of about 180. It exited the whole worker on the first sentence, so a
  job sat at "0/11" for ever. A short copy of the data is now used, and a start-up self-check turns any remaining
  failure into a clear error (also shown by `setup_check` and `claudio-audiobook doctor`).
- Fix: a worker that died stayed "running" for ever (a finished child nobody has reaped still has a process id).
  Dead workers are now reaped and reported as failed with their last output, which is kept in a log file.
- Fix: `${HOME}` and `~` are expanded in the default folder, `output_dir` and `file`; blank or unfilled
  `${user_config.…}` settings fall back to defaults. The Desktop manifest no longer sets a `${HOME}` default.
- New: progress is reported inside a chapter ("part 3/9"), a start message with the real absolute folder, and a
  warning when a live worker makes no progress for 3 minutes.

## 0.1.0

- First version, split out of claudio-tts. CLI (`claudio-audiobook build`), MCP server for Claude Code (plugin) and
  Claude Desktop (`.mcpb`), and a skill. Every Kokoro setting: voice and voice blends, speed, language, sentence,
  clause and chapter pauses, trim, full or lite model. m4b with chapter marks, mp3 or wav through a bundled ffmpeg.
  Resumable, background jobs that survive a restart.
