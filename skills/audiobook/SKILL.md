---
name: audiobook
description: Create an audiobook from a topic, a pasted text or a file, with local Kokoro voices (no API key, nothing uploaded). Use when the user asks for an audiobook, a spoken course or lesson as audio, or to turn a text or markdown file into audio, e.g. "create a python course audiobook".
---

# Audiobook

Uses the `claudio-audiobook` MCP tools: `make_audiobook`, `audiobook_status`, `list_voices`, `setup_check`.

1. **Scope.** Agree topic, level, rough length (about 150 spoken words a minute), and voice/speed if the user
   cares. Ask only what you cannot reasonably assume. If the user already has a file, skip to step 3 with `file`.
2. **Write the text yourself** as markdown for the ear: one `# ` heading per chapter (the title is read aloud),
   a short welcome first and a short closing chapter, short sentences. No code blocks, tables, URLs or emoji;
   they are skipped or read badly. Say code in words ("call print with the text hello"). For a long course, write
   chapter by chapter instead of one giant message.
3. **Preview.** Call `make_audiobook` with the text as `markdown` and `dry_run=true`; show the chapter list and
   estimated length. Adjust if the user wants.
4. **Render.** Call it again without `dry_run`. Everything Kokoro allows is an argument: `voice` (a name such as
   `af_heart`, or a blend `"af_heart:0.6,af_sky:0.4"`; see `list_voices`), `speed` (0.5-2.0), `lang` (e.g. `de`),
   `sentence_pause`, `clause_pause`, `chapter_pause` (seconds), `trim`, `model_variant` (`full`/`lite`),
   `format` (`m4b` with chapter marks, `mp3`, `wav`), `output_dir`, `force`. Book tags and cover: `author`,
   `narrator`; a title cover is generated locally, so pick `cover_colors` (`"#top,#bottom"`) that suit the topic,
   or pass `cover` with the path of the user's own image (`"none"` for no cover).
5. **Follow.** Poll `audiobook_status` with the job id until `done` (the first run also downloads the ~330 MB voice
   model once). Report the output path. If it failed, show the message and offer to rerun: finished chapters are
   kept, so a rerun resumes.

Everything stays on the user's machine. Never upload or share the audio unless the user asks.
