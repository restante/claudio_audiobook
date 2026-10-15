# 🎧 claudio-audiobook

### Say "create a python course audiobook". Get an audiobook. Locally, for free.

Claude writes the text, a local [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) voice reads it. No API key,
no account, no per-word cost, and nothing leaves your computer. Works in **Claude Code** and **Claude Desktop**.

Output is one `.m4b` file with chapters (or `.mp3` / `.wav`), saved in `~/Audiobooks/<title>/`.

## Install

You need [uv](https://docs.astral.sh/uv/) for Claude Code (`curl -LsSf https://astral.sh/uv/install.sh | sh`;
Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`). Everything else, including ffmpeg, is
installed for you. The voice model (about 330 MB, once) downloads on first use.

**Claude Code**

```text
/plugin marketplace add restante/claudio_audiobook
/plugin install claudio-audiobook --marketplace restante/claudio_audiobook
```

or just the MCP server, without the skill:

```bash
claude mcp add claudio-audiobook -- uvx --from git+https://github.com/restante/claudio_audiobook claudio-audiobook-mcp
```

**Claude Desktop**

Download `claudio-audiobook-<version>.mcpb` from the [Releases](https://github.com/restante/claudio_audiobook/releases)
page and open it with Claude Desktop (Settings → Extensions). Desktop installs the dependencies itself. Set your
default voice, speed and folder in the extension's settings if you like.

## Use

Just ask:

> create a python course audiobook, for beginners, about an hour, in a calm British voice

Claude agrees the scope, writes the course as spoken prose, shows the chapter list and length, then renders it in
the background and tells you where the file is. Ask for changes the same way: *"slower"*, *"a different voice"*,
*"mix af_heart and bf_emma 60/40"*, *"longer pauses between sentences"*, *"make it mp3"*.

Already have text? *"Turn ~/notes/book.md into an audiobook."* Chapters start at `# headings` (or lines like
`Chapter 3`); a file without headings is cut into parts.

## Every setting

Available as MCP tool arguments, CLI flags, and (for the first five) defaults in the Desktop settings or the
`CLAUDIO_AUDIOBOOK_*` environment variables.

| Setting | CLI flag | Values | Default |
|---|---|---|---|
| voice | `--voice` | a name (`af_heart`, `bf_emma`, `im_nicola`, … 54 voices, 9 languages) or a blend `af_heart:0.6,af_sky:0.4` | `af_heart` |
| speed | `--speed` | 0.5 to 2.0 | 1.0 |
| language | `--lang` | espeak code, e.g. `de`; lets a voice read another language with an accent | the voice's own |
| model | `--model` | `full` (best) or `lite` (92 MB, faster) | `full` |
| format | `--format` | `m4b` (chapters), `mp3`, `wav` | `m4b` |
| sentence pause | `--sentence-pause` | 0 to 5 seconds | 0.25 |
| clause pause | `--clause-pause` | 0 to 5 seconds (after commas, colons) | 0.1 |
| chapter pause | `--chapter-pause` | 0 to 30 seconds | 1.5 |
| trim | `--no-trim` | cut silence at sentence ends, or keep it | trim |
| output folder | `-o` / `output_dir` | any folder | `~/Audiobooks/<title>` |

List voices with `claudio-audiobook voices`. `--dry-run` shows the chapters and the estimated length without
rendering. Interrupted? Run it again: finished chapters are kept, and only chapters whose text or settings changed
are redone (`--force` redoes everything).

## Command line

```bash
uvx --from git+https://github.com/restante/claudio_audiobook claudio-audiobook build book.md --voice bf_emma --speed 0.95
claudio-audiobook doctor        # check the install
```

## Privacy

The only network use is the one-time download of the Kokoro model from its GitHub release, checked against a
SHA-256 sum. Your text and audio never leave your machine.

## Develop

See `CLAUDE.md`. `uv venv --python 3.12 && uv pip install -e ".[dev]" && .venv/bin/pytest`.

MIT. Voices by [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).
