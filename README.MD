# ytSummery

A command-line tool that turns a YouTube video into a Markdown note. Give it a link, and it fetches the transcript, has an AI model summarize it, and saves the result as a `.md` file. The notes have frontmatter and tags, so they drop straight into Obsidian or any other Markdown notes app.

## Features

- **Transcript fetching:** uses YouTube's own captions when the video has them. When it doesn't, the audio is downloaded and transcribed locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
- **AI summaries:** a short summary, key points grouped by topic, and takeaways, generated through [OpenRouter](https://openrouter.ai).
- **Auto tags:** the model suggests 3–6 topic tags, which are added to the note's frontmatter next to `youtube` and `summary`.
- **Model fallback:** if one model hits a rate limit or errors, the next one in the list is tried.
- **Nothing lost:** if every model fails, the raw transcript is saved instead.
- **Safe filenames:** characters that break filenames are removed, and an existing note is never overwritten (`Title (2).md`, `Title (3).md`, ...).

## Requirements

- Python 3.10+
- An [OpenRouter API key](https://openrouter.ai/keys)

## Installation

```bash
git clone <repo-url>
cd youtube_summery

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

This installs the dependencies from `requirements.txt` and adds the `ytsum` command.

## Setup

Copy the example env file and add your OpenRouter key:

```bash
cp .env.example .env
```

```env
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

You can also export `OPENROUTER_API_KEY` in your shell. If you don't use an editable install (`-e`), you need to do this, because the `.env` file in the repo won't be found.

## Usage

Summarize a video:

```bash
ytsum "https://www.youtube.com/watch?v=VIDEO_ID"
```

`youtube.com/watch?v=`, `youtu.be/`, `/shorts/` and `/embed/` links all work.

Choose where notes are saved (the default is `~/Documents/Notes`):

```bash
ytsum --set-output ~/Obsidian/Vault/YouTube
```

Show the current save folder:

```bash
ytsum --show-output
```

The save folder is stored in `~/.config/yt-summarizer/config.json`.

## Output

Each note looks like this:

```markdown
---
title: "Video Title"
source: https://www.youtube.com/watch?v=VIDEO_ID
date: 2026-11-04
tags: [youtube, summary, machine-learning, python]
---

# Video Title

## Summary
...

## Key Points
### Topic one
- ...

## Takeaways
- ...
```

If summarizing fails, the transcript is saved as `Video Title (transcript).md` with the tags `youtube, transcript`.

## Models

The models are listed in `PROVIDER` in `src/summery.py` and tried in order:

| Name | Model ID |
| --- | --- |
| Nemotron 3 Ultra (free) | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| Gemma 4 31B (free) | `google/gemma-4-31b-it:free` |
| GLM 5.3 Flash | `z-ai/glm-5.3-flash` |

To add, remove or reorder models, edit that list. Any model on OpenRouter will work.

## Project structure

```
src/
  main.py        # CLI entry point (ytsum)
  transcript.py  # video ID, title, transcript (captions or Whisper)
  summery.py     # OpenRouter calls, model fallback, tag parsing
  save.py        # builds the Markdown note and writes it to disk
  config.py      # reads and saves the output folder
test/            # pytest tests for each module
```

## Running tests

```bash
pytest
```

The tests use a dummy API key and never call the real API.

## Notes

- The first time a video without captions is transcribed, the Whisper `small` model is downloaded, which can take a while. Transcribing runs on your machine, so long videos can be slow.
- Only English captions are requested from YouTube. For other languages, the tool falls back to Whisper.
