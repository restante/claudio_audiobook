<div align="center">

# 🎧 claudio-audiobook

### An MCP server that lets your AI assistant make audiobooks
**Say *"create a python course audiobook"*. The AI writes it, a local voice reads it. Free, private, offline.**

**Works with** Claude Desktop · Claude Code · Cursor · VS Code (Copilot) · Gemini CLI · Codex CLI · any MCP client

[![CI](https://github.com/restante/claudio_audiobook/actions/workflows/ci.yml/badge.svg)](https://github.com/restante/claudio_audiobook/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/restante/claudio_audiobook/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/restante/claudio_audiobook)](https://github.com/restante/claudio_audiobook/releases)
[![MCP server](https://img.shields.io/badge/MCP-server-8A2BE2)](https://modelcontextprotocol.io)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Runs locally](https://img.shields.io/badge/runs-100%25%20locally-brightgreen)

[**Install**](#install-in-60-seconds) · [**Listen**](#hear-it) · [**Examples**](#examples) · [**Voices**](#54-voices-9-languages) · [**Settings**](#every-setting)

<!-- HERO: docs/img/hero.gif — see docs/SCREENSHOTS.md, shot 1. Add it here once captured. -->

</div>

---

## What it is

claudio-audiobook is a **[Model Context Protocol](https://modelcontextprotocol.io) (MCP) server**. You add it to an
AI assistant, and the assistant gains the ability to turn text into an audiobook on your computer. It is built
and tested first for **Claude** (Desktop and Code, as a one-click extension and a plugin), and it works with
other MCP-capable tools too. It also has a plain command line for use without any AI.

| Tool | How to install |
|---|---|
| Claude Desktop | one-click `.mcpb` extension |
| Claude Code | plugin, or `claude mcp add` |
| Cursor | [`mcp.json`](#other-ai-tools) |
| VS Code (GitHub Copilot) | [`mcp.json`](#other-ai-tools) |
| Gemini CLI | [`settings.json`](#other-ai-tools) |
| Codex CLI (OpenAI) | [`config.toml`](#other-ai-tools) |
| Any other MCP client, or no AI | stdio command / [command line](#command-line) |

Not supported: web chat apps that cannot run local MCP servers (the ChatGPT and Gemini websites).

## Why

Text-to-speech APIs charge per character and send your text to someone else's server. Audiobook apps only play
books that already exist. **claudio-audiobook closes the gap:** you describe the audiobook you want, Claude
writes it as spoken prose, and an 82M-parameter [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) voice reads it
on your own machine.

|  | claudio-audiobook | Cloud TTS APIs | Audiobook apps |
|---|:-:|:-:|:-:|
| Creates the *content* for you | ✅ | ❌ | ❌ |
| Cost per hour of audio | **£0** | per-character fees | subscription |
| Text leaves your computer | **Never** | Always | n/a |
| API key or account | **None** | Required | Required |
| Chapters in the file (`.m4b`) | ✅ | DIY | ✅ |
| Works offline after setup | ✅ | ❌ | partly |

## Hear it

Real output, no editing. Voice `bf_emma`, from the text in [`docs/samples/python-intro.md`](https://github.com/restante/claudio_audiobook/blob/main/docs/samples/python-intro.md):

▶ **[python-intro-bf_emma.mp3](https://github.com/restante/claudio_audiobook/releases/download/v0.1.2/python-intro-bf_emma.mp3)** (18 seconds, 109 KB)

That sample rendered in about 6 seconds on the author's Mac (CPU only). A real 11-chapter, 36-minute exam course took about
3 minutes.

## Install in 60 seconds

You need [uv](https://docs.astral.sh/uv/) for Claude Code ([install it](https://docs.astral.sh/uv/getting-started/installation/):
macOS `brew install uv`, Windows `winget install --id=astral-sh.uv -e`). Everything else, including ffmpeg, is
installed for you. The voice model (about 330 MB, once) downloads on first use.

### Claude Code

```text
/plugin marketplace add restante/claudio_audiobook
/plugin install claudio-audiobook --marketplace restante/claudio_audiobook
```

Prefer just the MCP server, without the skill?

```bash
claude mcp add claudio-audiobook -- uvx --from git+https://github.com/restante/claudio_audiobook claudio-audiobook-mcp
```

### Claude Desktop

1. Download `claudio-audiobook-<version>.mcpb` from [Releases](https://github.com/restante/claudio_audiobook/releases).
2. Open it with Claude Desktop (Settings → Extensions).
3. Optional: set your default voice, speed and folder in the extension's settings.

Desktop installs the dependencies itself.

## Other AI tools

It is a standard MCP server (stdio), so it is not tied to Claude. Install it once, then point your tool at it:

```bash
uv tool install git+https://github.com/restante/claudio_audiobook   # puts claudio-audiobook-mcp on your PATH
claudio-audiobook download-model                                    # the voice model, about 330 MB, once
claudio-audiobook doctor                                            # checks everything is in place
```

Installing first matters: the first run of `uvx --from git+…` has to fetch and build everything, which can
exceed a client's start-up timeout. If your tool cannot find the command, use its full path (`which claudio-audiobook-mcp`).

<details>
<summary><b>Cursor</b> · <code>~/.cursor/mcp.json</code> or <code>.cursor/mcp.json</code></summary>

```json
{
  "mcpServers": {
    "claudio-audiobook": {
      "type": "stdio",
      "command": "claudio-audiobook-mcp"
    }
  }
}
```
</details>

<details>
<summary><b>VS Code (GitHub Copilot)</b> · <code>.vscode/mcp.json</code> or run <i>MCP: Open User Configuration</i></summary>

```json
{
  "servers": {
    "claudio-audiobook": {
      "type": "stdio",
      "command": "claudio-audiobook-mcp"
    }
  }
}
```
Use agent mode so Copilot can call tools.
</details>

<details>
<summary><b>Gemini CLI</b> · <code>~/.gemini/settings.json</code></summary>

```json
{
  "mcpServers": {
    "claudio-audiobook": {
      "command": "claudio-audiobook-mcp"
    }
  }
}
```
or `gemini mcp add --scope user claudio-audiobook claudio-audiobook-mcp`. Check with `/mcp`.
</details>

<details>
<summary><b>Codex CLI (OpenAI)</b> · <code>~/.codex/config.toml</code></summary>

```toml
[mcp_servers.claudio-audiobook]
command = "claudio-audiobook-mcp"
startup_timeout_sec = 60
```
or `codex mcp add claudio-audiobook -- claudio-audiobook-mcp`. Codex waits only 10 seconds for a server to start
by default, so raise `startup_timeout_sec` as above. Check with `codex mcp list`.
</details>

Set defaults (voice, speed, folder) with `CLAUDIO_AUDIOBOOK_*` environment variables in the same config, for example
`"env": { "CLAUDIO_AUDIOBOOK_VOICE": "bf_emma" }`. Any agent that can run a shell can also use the
[command line](#command-line) directly.

> **Status:** the server was checked with a generic MCP stdio client (handshake, tool list, a dry run), and the
> tool schemas are tested to avoid constructs that Cursor and Gemini mishandle. The configs above follow each
> tool's current documentation but have not yet been run inside those tools. If one doesn't work for you,
> please [open an issue](https://github.com/restante/claudio_audiobook/issues).

## Examples

Just ask. Claude agrees the scope, writes the text, shows the chapter list and length, renders in the background
and tells you where the file is.

**A course from nothing**

> create a python course audiobook, for beginners, about an hour, in a calm British voice

**Your own text**

> Turn ~/notes/book.md into an audiobook.

**Steer it in plain English**

> slower · a different voice · mix af_heart and bf_emma 60/40 · longer pauses between sentences · make it mp3

**Ideas people can do with it**

- 🎓 Revision notes or an exam course you can listen to on the commute
- 📰 A long article or paper, read aloud while you cook
- 🧒 A bedtime story, in a voice you picked
- 🌍 Language practice: an Italian text read by `if_sara`, or an English text read with a French accent
- 💼 Onboarding docs or a team handbook as a podcast-style audio file

**What you get**

```text
~/Audiobooks/python-for-beginners/
├── python-for-beginners.m4b      ← one file, with chapter marks
├── 01-welcome.wav
├── 02-variables.wav
└── ...
```

<!-- SCREENSHOT: Claude Desktop chat producing a course — docs/img/desktop-chat.png (docs/SCREENSHOTS.md, shot 2) -->
<!-- SCREENSHOT: the finished .m4b in Apple Books / Podcasts showing chapters — docs/img/chapters.png (shot 3) -->

### Command line

A real run (from [`docs/samples/python-intro.md`](https://github.com/restante/claudio_audiobook/blob/main/docs/samples/python-intro.md)): three chapters in, one `.m4b`
with chapter marks out.

![Terminal: claudio-audiobook builds an m4b with three chapters](https://raw.githubusercontent.com/restante/claudio_audiobook/main/docs/img/terminal.png)


No Claude needed for text you already have:

```bash
uvx --from git+https://github.com/restante/claudio_audiobook \
  claudio-audiobook build book.md --voice bf_emma --speed 0.95
```

Preview before rendering. This is real output:

```text
$ claudio-audiobook build course.md --dry-run
  1  01-welcome.wav                                 ~  0.1 min
  2  02-variables.wav                               ~  0.1 min
  3  03-loops.wav                                   ~  0.1 min
3 chapters, about 0.0 h of audio
```

Chapters start at `# headings` (or lines like `Chapter 3`); a file without headings is cut into parts.
Interrupted? Run it again: finished chapters are kept, and only chapters whose text or settings changed are redone.

## Play it anywhere: chapters, tags and cover art

The default output is an **M4B**, the standard audiobook file: AAC audio with chapter marks, the tags players use
to file it under *Audiobooks* (title, author, narrator, genre "Audiobook"), and a cover.

<img src="https://raw.githubusercontent.com/restante/claudio_audiobook/main/docs/img/cover-example.jpg" alt="A generated title cover" width="220" align="right">

- **Cover art is made for you**, locally. Ask the AI for a look (*"a dark green cover"*): it picks the colours and
  passes them as `cover_colors`. Or give your own picture: *"use ~/Pictures/cover.png"* (`--cover`). A
  `cover.jpg` or `cover.png` you drop in the book's folder is used too. `--cover none` skips it.
- **Author and narrator** come from the chat (*"by Ada Lovelace"*) or the `--author` flag. Set a default author
  once in the Desktop extension settings.
- The generated cover uses the built-in Latin font: titles in Chinese, Japanese or Korean show empty boxes, so give
  those books their own cover image.

Import it into:

| Where | How |
|---|---|
| **Apple Books** (Mac, iPhone, iPad) | drag the `.m4b` onto Books, or share it from Files |
| **BookPlayer** (iOS, chapters tested), **Audiobookshelf**, **Plex** | add it to the library folder or import it |
| **Voice**, **Smart AudioBook Player**, **Listen** (Android) | open the file or copy it to your audiobooks folder |
| VLC, Foobar2000 | plays it. VLC for iOS did not show the chapter list in testing, so use BookPlayer or Apple Books for chapters |

Choose `--format mp3` for players that don't read M4B (some car stereos). Audible and Kindle use closed formats
and cannot import it.

## 54 voices, 9 languages

```text
American English: af_heart, af_bella, af_nova, am_adam, am_michael, ...
British English:  bf_emma, bf_isabella, bm_george, bm_lewis, ...
Italian:          if_sara, im_nicola
Spanish:          ef_dora, em_alex          French: ff_siwis
Hindi, Japanese, Brazilian Portuguese, Mandarin Chinese ...
```

Blend two voices into a new one: `--voice af_heart:0.6,bf_emma:0.4`. List them all with `claudio-audiobook voices`.

## Every setting

Available as MCP tool arguments, CLI flags, and (for the first five, and the author) defaults in the Desktop settings or the
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
| author | `--author` | shown by players as the author | `CLAUDIO_AUDIOBOOK_AUTHOR`, else none |
| narrator | `--narrator` | shown as the narrator | `Kokoro (<voice>)` |
| cover | `--cover` | `.jpg`/`.png` path, `none`, or leave out to generate a title cover | generated |
| cover colours | `--cover-colors` | `#top,#bottom` for the generated cover | picked from the title |
| output folder | `-o` / `output_dir` | any folder | `~/Audiobooks/<title>` |

`--dry-run` shows the chapters and the estimated length without rendering. `--force` redoes everything.
`claudio-audiobook doctor` checks the install.

## How it works

```text
 "create a python course"
          │
          ▼
   Claude writes spoken-style markdown   ← the skill / prompt teaches it to write for the ear
          │
          ▼
   MCP server: make_audiobook            ← runs as a detached job; survives a restart of Claude
          │
          ▼
   Kokoro (ONNX) renders each chapter    ← local, resumable, voice blends, pauses
          │
          ▼
   ffmpeg packs .m4b with chapter marks  ← bundled, nothing to install
```

Four MCP tools (`make_audiobook`, `audiobook_status`, `list_voices`, `setup_check`), a `write_audiobook` prompt
and an `audiobook` skill. Works with any MCP client that can run a local stdio server.

## Privacy

The only network use is the one-time download of the Kokoro model from its GitHub release, checked against a
SHA-256 sum. Your text and audio never leave your machine. No telemetry, no accounts.

## FAQ

**Does it cost anything?** No. Claude itself is whatever plan you already have; the voice is free and local.

**How good is the voice?** Judge for yourself: [listen to the sample](#hear-it). Kokoro is among the best small
open TTS models, but it is not a human narrator. Expect clean, natural reading with occasional odd stress on
unusual names.

**Does it need a GPU?** No. It runs on CPU.

**Windows / Linux?** The code is cross-platform and CI runs the tests. macOS is the tested path for Claude Desktop;
Windows is not yet tested end to end. Reports welcome.

**Can I use a different voice model?** Point `CLAUDIO_AUDIOBOOK_MODEL_FILE` and `CLAUDIO_AUDIOBOOK_VOICES_FILE` at
your own copy of the Kokoro files.

## Contributing

Issues and PRs welcome, especially: Windows testing, new languages, and sample audiobooks. See
[`CLAUDE.md`](https://github.com/restante/claudio_audiobook/blob/main/CLAUDE.md) for architecture and rules.

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]" && .venv/bin/pytest
```

If this saved you a subscription, a ⭐ helps others find it.

MIT. Voices by [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) via
[kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).
