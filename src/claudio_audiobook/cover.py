"""Cover art: a generated title cover (local, no network), or the person's own image, as a JPEG."""

from __future__ import annotations

import colorsys
import hashlib
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1400  # square; players want at least ~1400 px
GENERATED = "cover.generated.jpg"
EMBED = ".cover-embed.jpg"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")

RGB = tuple[int, int, int]


def _rgb(value: str) -> RGB:
    match = _HEX.match(value.strip())
    if not match:
        raise ValueError(f"{value!r} is not a hex colour like #1f3a5f")
    n = int(match.group(1), 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def _darker(color: RGB) -> RGB:
    return tuple(int(c * 0.45) for c in color)  # type: ignore[return-value]


def parse_colors(spec: str) -> tuple[RGB, RGB] | None:
    """'#top,#bottom' (one colour gets a darker partner); '' means choose from the title."""
    spec = (spec or "").strip()
    if not spec:
        return None
    parts = [p for p in spec.split(",") if p.strip()]
    if not 1 <= len(parts) <= 2:
        raise ValueError("give one or two hex colours, like #1f3a5f,#4a7ab5")
    top = _rgb(parts[0])
    return top, _rgb(parts[1]) if len(parts) == 2 else _darker(top)


def default_colors(title: str) -> tuple[RGB, RGB]:
    """A pleasant gradient picked from the title, so each book looks different but is repeatable."""
    hue = int(hashlib.sha256(title.encode()).hexdigest()[:8], 16) % 360 / 360
    top = colorsys.hls_to_rgb(hue, 0.42, 0.55)
    bottom = colorsys.hls_to_rgb((hue + 0.08) % 1, 0.18, 0.60)
    return tuple(int(c * 255) for c in top), tuple(int(c * 255) for c in bottom)  # type: ignore


def _luminance(color: RGB) -> float:
    r, g, b = (c / 255 for c in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def _fit_title(draw, title: str, width: int, height: int):
    """The largest font size at which the wrapped title fits the box."""
    for size in range(170, 49, -6):
        font = ImageFont.load_default(size=size)
        lines = _wrap(draw, title, font, width)
        line_h = int(size * 1.18)
        too_wide = any(draw.textlength(ln, font=font) > width for ln in lines)
        if not too_wide and line_h * len(lines) <= height:
            return font, lines, line_h
    font = ImageFont.load_default(size=50)
    line_h = 59
    lines = _wrap(draw, title, font, width)[: height // line_h]
    if lines:
        lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return font, lines, line_h


def generate(
    path: Path, title: str, author: str = "", colors: tuple[RGB, RGB] | None = None
) -> Path:
    """Write a title cover as a JPEG at `path`: a vertical gradient, the title, the author."""
    top, bottom = colors or default_colors(title)
    img = Image.new("RGB", (SIZE, SIZE))
    pixels = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        pixels.line(
            [(0, y), (SIZE, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)),
        )
    average = tuple((a + b) // 2 for a, b in zip(top, bottom, strict=True))
    ink = (255, 255, 255) if _luminance(average) < 0.6 else (24, 24, 32)  # type: ignore[arg-type]
    draw = ImageDraw.Draw(img)
    margin = 130
    box_w, box_h = SIZE - 2 * margin, 760
    font, lines, line_h = _fit_title(draw, title or "Audiobook", box_w, box_h)
    block = line_h * len(lines)
    y = 220 + (box_h - block) // 2
    for line in lines:
        width = draw.textlength(line, font=font)
        draw.text(((SIZE - width) / 2, y), line, font=font, fill=ink)
        y += line_h
    draw.rectangle([SIZE // 2 - 90, 1060, SIZE // 2 + 90, 1066], fill=ink)
    if author:
        a_font, a_lines, a_h = _fit_title(draw, author, box_w, 160)
        a_font = ImageFont.load_default(size=min(getattr(a_font, "size", 64), 70))
        a_y = 1110
        for line in _wrap(draw, author, a_font, box_w)[:2]:
            width = draw.textlength(line, font=a_font)
            draw.text(((SIZE - width) / 2, a_y), line, font=a_font, fill=ink)
            a_y += 82
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=90)
    return path


def normalise(source: Path, target: Path) -> Path:
    """The person's image as an RGB JPEG at `target` (so any PNG or JPEG embeds the same way)."""
    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((2000, 2000))
        img.save(target, "JPEG", quality=92)
    return target


def check_image(path: Path) -> None:
    """Raises ValueError if `path` is not a readable PNG or JPEG."""
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("a cover must be a .jpg, .jpeg or .png file")
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as error:  # Pillow raises several types for a bad file
        raise ValueError(f"cannot read the cover image: {error}") from error


def dropped_in(outdir: Path) -> Path | None:
    """A cover the person put in the book's folder (cover.jpg / cover.png), if any."""
    for name in ("cover.jpg", "cover.jpeg", "cover.png"):
        if (outdir / name).is_file():
            return outdir / name
    return None
