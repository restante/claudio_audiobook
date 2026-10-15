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
