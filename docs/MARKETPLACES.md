# Distribution plan (draft, nothing here has been submitted)

Every submission is public. Do them only when the owner says so. Requirements change often: **check each
listing's current instructions before submitting**, this list is from memory and unverified.

## Before submitting anything
- [ ] Real screenshots/GIF in the README (`docs/SCREENSHOTS.md`)
- [ ] Release-page `.mcpb` install confirmed on a clean Claude Desktop (HANDOVER open item 2)
- [ ] Repo topics set: `mcp`, `mcp-server`, `claude-code`, `claude-desktop`, `tts`, `kokoro`, `audiobook`, `text-to-speech`, `local-ai`
- [ ] Social preview image set
- [ ] Decide on PyPI: several registries prefer an installable package over a git URL

## Where it can go
| Where | What it takes | Status |
|---|---|---|
| Own Claude Code marketplace (`.claude-plugin/`) | Already works: `/plugin marketplace add restante/claudio_audiobook` | done |
| Anthropic Claude Code plugin directory | Submission via Anthropic's process | not started |
| Claude Desktop extension directory (`.mcpb`) | Submission via Anthropic's process; needs a clean install and likely a privacy statement (README has one) | not started |
| Official MCP Registry | `server.json` + publish with the registry tool; a PyPI package is the usual route | needs PyPI |
| `awesome-mcp-servers` lists | A pull request adding one line | not started |
| Smithery, Glama, PulseMCP, mcp.so | Some index public GitHub MCP repos automatically, some want a claim or form | not started |

## Launch post (draft, not posted)
Hacker News "Show HN", r/ClaudeAI, r/LocalLLaMA. Lead with the audio sample and the privacy angle (local, no key).
Write the post in a file first and let the owner approve it.

## Plugin directory validation (15 Oct 2026: 109c7ee had 4 warnings and 3 holds; 70ada8c has 3 and 3)

Fixed in the repo:
- README no longer pipes a download into a shell to install uv (it links uv's install page). Don't quote that
  pattern in any file: the scanner flags the text itself, as it did in this file on the second run.
- No opaque binaries or SVG in the tree: the sample mp3 is a release asset, the terminal image is a PNG.
- `.claude-plugin/icon.png` added (1024 px, square). The portal keeps the icon from the first save or
  submission only, so check it before submitting.

Still open, and why:
- **Lockfile / pinned launcher.** The directory wants a `uv.lock` next to the manifest and a launcher of the form
  `uvx <package>==<version>`. That needs the package on PyPI. A full `uv.lock` is about 368 KB, over the 256 KiB
  per-file limit; one restricted to Python 3.12+ and three platforms is 250 KB, just under. Decide on PyPI first.
- **Credential + network hold.** There is no credential in the code. The scanner matched environment-variable
  reads (settings, `HOME`) plus one `urlopen` (model download from the Kokoro GitHub release, SHA-256 checked, in
  `model.py`). Leave it and let a reviewer confirm, or ask them what exactly matched.
- **CLAUDE.md at the plugin root** is not loaded as plugin context. It is repo guidance; harmless.

Second run (`70ada8c`): the icon warning and the image/binary findings cleared (icon, cover and terminal images were
all "let through"). Still held: the lockfile, the credential heuristic, and one "file that nothing runs" hold whose
file the report does not name (expand the hold in the portal to see which).
