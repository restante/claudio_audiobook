"""Text to chapters: split a document, and turn markdown into plain text that sounds right."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass

import mistune

CHUNK_CHARS = 3000  # fallback chapter size when the text has no headings
CHARS_PER_SECOND = 15  # rough speaking rate at speed 1.0, for estimates and the fake synthesiser
MARKDOWN_SUFFIXES = {".md", ".markdown"}

_parse = mistune.create_markdown(renderer="ast", plugins=["strikethrough", "table"])
_URL = re.compile(r"https?://\S+")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SPACES = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n{3,}")
_EMOJI = re.compile("[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f2ff️‍]+")
_HEADING = re.compile(
    r"^(?:#{1,3}\s+(?P<md>\S.*?)\s*#*|(?P<word>(?:chapter|capitolo|kapitel|chapitre|cap[ií]tulo)"
    r"\s+[\w.]+\b.*?))\s*$",
    re.IGNORECASE,
)


def _inline(nodes: list[dict]) -> str:
    out: list[str] = []
    for node in nodes:
        kind = node["type"]
        if kind == "text":
            out.append(node["raw"])
        elif kind in ("strong", "emphasis", "strikethrough", "link", "image"):
            out.append(_inline(node.get("children", [])))
        elif kind in ("softbreak", "linebreak"):
            out.append(" ")
        # codespan, inline_html: dropped on purpose
    return "".join(out)


def _block(nodes: list[dict]) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        kind = node["type"]
        if kind in ("paragraph", "block_text"):
            lines.append(_inline(node.get("children", [])).strip())
        elif kind == "heading":
            text = _inline(node.get("children", [])).strip()
            lines.append(text if text.endswith((".", "!", "?", ":")) else text + ".")
        elif kind in ("list", "block_quote", "list_item"):
            lines.extend(_block(node.get("children", [])))
        elif kind == "table":
            for part in node.get("children", []):
                for row in part.get("children", []):
                    cells = [
                        _inline(c.get("children", [])).strip() for c in row.get("children", [])
                    ]
                    lines.append(", ".join(c for c in cells if c) + ".")
        # block_code, thematic_break, block_html: dropped on purpose
    return lines


def clean(text: str) -> str:
    """Plain, speakable text. Code blocks and inline code are dropped, links keep their label."""
    text = _COMMENT.sub("", text)
    out = "\n".join(line for line in _block(_parse(text)) if line)
    out = html.unescape(out)
    out = _URL.sub("link", out)
    out = _EMOJI.sub("", out)
    out = unicodedata.normalize("NFKC", out)
    out = _SPACES.sub(" ", out)
    out = _BLANKS.sub("\n\n", out)
    return out.strip()


@dataclass
class Chapter:
    title: str
    text: str
    announce: bool = True  # read the title aloud before the body

    def spoken(self, is_markdown: bool) -> str:
        body = clean(self.text) if is_markdown else self.text
        return f"{self.title}.\n\n{body}" if self.announce else body


def split_chapters(text: str) -> list[Chapter]:
    """Split on markdown headings or "Chapter N" lines; without any, on paragraph-bounded chunks."""
    text = text.replace("\r\n", "\n").strip()
    chapters: list[Chapter] = []
    title, body = "Introduction", []

    def flush(announce: bool) -> None:
        joined = "\n".join(body).strip()
        if joined:
            chapters.append(Chapter(title, joined, announce))

    found, in_fence = False, False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line.strip())
        if match:
            flush(announce=found)  # text before the first heading is not announced
            found = True
            title, body = (match.group("md") or match.group("word")).strip(), []
        else:
            body.append(line)
    flush(announce=found)
    return chapters if found else _chunks(text)


def _chunks(text: str) -> list[Chapter]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) > CHUNK_CHARS:
            chunks.append(current)
            current = ""
        current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        chunks.append(current)
    return [Chapter(f"Part {i}", c, announce=False) for i, c in enumerate(chunks, 1)]


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def pieces(spoken: str, target: int = 400) -> list[str]:
    """Cut a chapter's text into pieces of about `target` characters on sentence ends, so progress
    can be reported inside a long chapter. Short sentences ("Three. Two. One.") are grouped."""
    out: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(" ".join(spoken.split())):
        current = f"{current} {sentence}" if current else sentence
        if len(current) >= target:
            out.append(current)
            current = ""
    if current:
        out.append(current)
    return out


def slug(title: str) -> str:
    cleaned = re.sub(r"[^\w]+", "-", title, flags=re.UNICODE).strip("-").lower()
    return cleaned[:40].strip("-") or "audiobook"
