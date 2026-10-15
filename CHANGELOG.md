# Changelog

## 0.1.1 (unreleased)

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
