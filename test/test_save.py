from datetime import date

import config
from save import build_content, clean_filename, save_md, save_transcript, unique_path


def test_removes_bad_characters():
    assert clean_filename("What is AI?") == "What is AI"
    assert clean_filename("???") == "untitled"
    assert clean_filename("a" * 300) == "a" * 100
    assert clean_filename("  .Titles.    ") == "Titles"
    assert clean_filename("What is Ai? | part 1/3") == "What is Ai  part 13"


def test_clean_filename_replaces_newlines_and_tabs():
    assert clean_filename("line one\nline\ttwo") == "line one line two"


def test_clean_filename_strips_after_cutting():
    # cut lands on a space, which should be trimmed off
    assert clean_filename("abc def", max_length=4) == "abc"


def test_unique_path_counts_up(tmp_path):
    assert unique_path(tmp_path, "note") == tmp_path / "note.md"
    (tmp_path / "note.md").touch()
    assert unique_path(tmp_path, "note") == tmp_path / "note (2).md"
    (tmp_path / "note (2).md").touch()
    assert unique_path(tmp_path, "note") == tmp_path / "note (3).md"


def test_build_content_has_frontmatter_and_heading():
    content = build_content('Say "hi"', "https://youtu.be/abc", "the body", tags="a, b")
    assert content.startswith("---\n")
    assert "title: \"Say 'hi'\"" in content
    assert "source: https://youtu.be/abc" in content
    assert f"date: {date.today()}" in content
    assert "tags: [a, b]" in content
    assert '# Say "hi"' in content
    assert content.rstrip().endswith("the body")


def test_save_md_writes_file(tmp_path):
    path = save_md("My Video?", "https://youtu.be/abc", "summary text", folder=tmp_path)
    assert path == tmp_path / "My Video.md"
    text = path.read_text(encoding="utf-8")
    assert "summary text" in text
    assert "tags: [youtube, summary]" in text


def test_save_md_adds_extra_tags_without_duplicates(tmp_path):
    path = save_md("t", "u", "s", folder=tmp_path, tags=["ai", "youtube", "python"])
    assert "tags: [youtube, summary, ai, python]" in path.read_text()


def test_save_md_creates_missing_folder(tmp_path):
    folder = tmp_path / "deep" / "notes"
    path = save_md("t", "u", "s", folder=folder)
    assert path.parent == folder
    assert path.exists()


def test_save_md_does_not_overwrite(tmp_path):
    first = save_md("Same", "u", "one", folder=tmp_path)
    second = save_md("Same", "u", "two", folder=tmp_path)
    assert first != second
    assert "one" in first.read_text()
    assert "two" in second.read_text()


def test_save_md_uses_config_folder_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr("save.get_output_dir", lambda: str(tmp_path))
    path = save_md("t", "u", "s")
    assert path.parent == tmp_path


def test_save_transcript(tmp_path):
    path = save_transcript("Vid", "u", "raw words", folder=tmp_path)
    assert path.name == "Vid (transcript).md"
    text = path.read_text()
    assert "raw words" in text
    assert "tags: [youtube, transcript]" in text
