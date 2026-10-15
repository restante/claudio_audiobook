from claudio_audiobook import text

BOOK = "Intro words here.\n\n# One\nFirst chapter text.\n\n# Two\nSecond chapter text.\n"


def test_split_on_markdown_headings():
    chapters = text.split_chapters(BOOK)
    assert [c.title for c in chapters] == ["Introduction", "One", "Two"]
    assert chapters[1].text == "First chapter text."


def test_text_before_first_heading_is_not_announced_but_chapters_are():
    chapters = text.split_chapters(BOOK)
    assert [c.announce for c in chapters] == [False, True, True]
    assert chapters[1].spoken(True).startswith("One.")
    assert chapters[0].spoken(True) == "Intro words here."


def test_split_on_chapter_lines():
    chapters = text.split_chapters("Chapter 1\nHello.\nChapter 2\nBye.")
    assert [c.title for c in chapters] == ["Chapter 1", "Chapter 2"]


def test_heading_inside_code_fence_is_not_a_chapter():
    body = "# Real\nbody\n```\n# not a chapter\n```\nmore"
    assert [c.title for c in text.split_chapters(body)] == ["Real"]


def test_no_headings_falls_back_to_paragraph_chunks():
    paragraph = "word " * 400
    chapters = text.split_chapters("\n\n".join([paragraph] * 4))
    assert len(chapters) >= 2 and all(c.title.startswith("Part ") for c in chapters)
    assert not any(c.announce for c in chapters)


def test_clean_drops_code_and_keeps_link_labels():
    out = text.clean("Use `print()` here.\n\n```py\nx = 1\n```\n\nSee [the docs](https://x.io).")
    assert "print" not in out and "x = 1" not in out and "the docs" in out and "https" not in out


def test_slug():
    assert text.slug("Python: The Basics!") == "python-the-basics"
    assert text.slug("???") == "audiobook"
