from types import SimpleNamespace

import pytest
import yt_dlp
from youtube_transcript_api import TranscriptsDisabled

import transcript
from transcript import (
    chunk_text,
    clean_transcript,
    get_title,
    get_transcript,
    get_video_id,
    stamp,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "dQw4w9WgXcQ",
    ],
)
def test_get_video_id(url):
    assert get_video_id(url) == "dQw4w9WgXcQ"


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL so no network is used."""

    def __init__(self, info=None, error=None):
        self.info = info
        self.error = error

    def __call__(self, opts):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        if self.error:
            raise self.error
        return self.info


def test_get_title(monkeypatch):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL(info={"title": "Cool Video"}))
    assert get_title("url") == "Cool Video"


def test_get_title_missing(monkeypatch):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL(info={}))
    assert get_title("url") == ""


def test_get_title_download_error(monkeypatch):
    error = yt_dlp.utils.DownloadError("nope")
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL(error=error))
    assert get_title("url") == ""


def fake_api(snippets=None, error=None):
    class FakeApi:
        def fetch(self, video_id, languages):
            if error:
                raise error
            return [SimpleNamespace(text=t, start=i * 5.0) for i, t in enumerate(snippets)]

    return FakeApi


def test_get_transcript_from_youtube(monkeypatch):
    monkeypatch.setattr(transcript, "YouTubeTranscriptApi", fake_api(["hello", "world"]))
    monkeypatch.setattr(transcript, "transscript_url", lambda url: pytest.fail("should not use whisper"))
    assert get_transcript("https://youtu.be/dQw4w9WgXcQ") == "[0:00] hello\n[0:05] world"


def test_get_transcript_falls_back_to_whisper(monkeypatch):
    api = fake_api(error=TranscriptsDisabled("dQw4w9WgXcQ"))
    monkeypatch.setattr(transcript, "YouTubeTranscriptApi", api)
    monkeypatch.setattr(transcript, "transscript_url", lambda url: "from whisper")
    assert get_transcript("https://youtu.be/dQw4w9WgXcQ") == "from whisper"


def test_get_transcript_returns_none_when_everything_fails(monkeypatch):
    api = fake_api(error=TranscriptsDisabled("dQw4w9WgXcQ"))
    monkeypatch.setattr(transcript, "YouTubeTranscriptApi", api)

    def broken(url):
        raise yt_dlp.utils.DownloadError("nope")

    monkeypatch.setattr(transcript, "transscript_url", broken)
    assert get_transcript("https://youtu.be/dQw4w9WgXcQ") is None


def test_get_transcript_empty_is_none(monkeypatch):
    monkeypatch.setattr(transcript, "YouTubeTranscriptApi", fake_api([]))
    assert get_transcript("https://youtu.be/dQw4w9WgXcQ") is None


@pytest.mark.parametrize(
    "seconds, expected",
    [(0, "[0:00]"), (75.9, "[1:15]"), (3725, "[1:02:05]")],
)
def test_stamp(seconds, expected):
    assert stamp(seconds) == expected


def test_clean_transcript_keeps_timestamps():
    raw = "[0:01] [Music] um so so I think &amp; that\n\n[0:04] >> uh ok"
    assert clean_transcript(raw) == "[0:01] so I think & that\n[0:04] ok"


def test_chunk_text_short_is_one_chunk():
    assert chunk_text("short text", max_chars=100) == ["short text"]


def test_chunk_text_splits_on_lines():
    lines = [f"[0:{i:02d}] line number {i}" for i in range(50)]
    text = "\n".join(lines)
    chunks = chunk_text(text, max_chars=100)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
    assert "\n".join(chunks) == text  # nothing lost, no line cut in half


def test_chunk_text_splits_long_line_by_words():
    text = "word " * 100
    chunks = chunk_text(text, max_chars=50)
    assert all(len(c) <= 50 for c in chunks)
    assert " ".join(chunks) == text.strip()
