from pathlib import Path
from datetime import date
from config import get_output_dir

DEFAULT_DIR = "~/Documents/Notes"


def write_note(folder, filename, content):
    """Create the folder if needed, pick a free path, write the file."""
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, filename)
    path.write_text(content, encoding="utf-8")
    return path


def clean_filename(title, max_length=100):
    """Remove characters that break filenames, cap the length,
    and never return an empty string."""
    chars_to_remove = r'\/:*?"<>|'
    clean_text = title.translate(str.maketrans("\n\t", "  ", chars_to_remove))
    clean_text = clean_text.strip(" .")
    clean_text = clean_text[:max_length].rstrip(" .")
    return clean_text or "untitled"


def unique_path(folder, name):
    """Return folder/name.md, or name (2).md, (3)... if it already exists."""
    path = folder / f"{name}.md"
    counter = 2
    while path.exists():
        path = folder / f"{name} ({counter}).md"
        counter += 1
    return path


def build_content(title, url, summary, tags="youtube, summary"):
    """Return the full note text: frontmatter, # heading, then the summary."""
    safe_title = title.replace('"', "'")
    content = f"""---
title: "{safe_title}"
source: {url}
date: {date.today()}
tags: [{tags}]
---

# {title}

{summary}
"""
    return content


def save_md(title, url, summary, folder=None):
    """Main function: pick the folder, create it if needed,
    build the content, write the file, return the path."""
    folder = Path(folder or get_output_dir()).expanduser()
    content = build_content(title, url, summary)
    return write_note(folder, clean_filename(title), content)


def save_transcript(title, url, transcript, folder=None):
    """Backup for when summarizing fails: save the raw transcript
    so the run isn't wasted."""
    folder = Path(folder or get_output_dir()).expanduser()
    content = build_content(title, url, transcript, tags="youtube, transcript")
    return write_note(folder, f"{clean_filename(title)} (transcript)", content)
