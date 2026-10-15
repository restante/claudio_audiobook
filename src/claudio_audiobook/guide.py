"""How to write text that makes a good audiobook. Used by the MCP server (instructions and the
`write_audiobook` prompt) and mirrored in skills/audiobook/SKILL.md for Claude Code."""

WRITING_GUIDE = """\
To make an audiobook (for example "create a python course audiobook"):
1. Agree the scope with the person: topic, level, rough length (about 150 spoken words a minute),
   voice and speed if they care. Ask only what you cannot reasonably assume.
2. Write the whole text yourself as markdown, as spoken prose: one "# " heading per chapter (the
   title is read aloud), a short welcome first and a short closing chapter. Short sentences. No code
   blocks, tables, URLs or emoji: they are skipped or read badly. Say code in words ("call print with
   the text hello"), and explain with examples the listener can follow by ear. For long courses write
   chapter by chapter rather than in one giant message.
3. Call make_audiobook with the text as `markdown` and dry_run=true to show the chapters and length;
   then call it again without dry_run to start the job.
4. Call audiobook_status with the job id until it is done (the first run also downloads the voice model,
   about 330 MB, once). Tell the person where the files are. Nothing is uploaded anywhere.
"""
