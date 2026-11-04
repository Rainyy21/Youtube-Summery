from types import SimpleNamespace

import pytest
import yt_dlp
from youtube_transcript_api import TranscriptsDisabled

import transcript
from transcript import get_title, get_transcript, get_video_id


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
            return [SimpleNamespace(text=t) for t in snippets]

    return FakeApi


def test_get_transcript_from_youtube(monkeypatch):
    monkeypatch.setattr(transcript, "YouTubeTranscriptApi", fake_api(["hello", "world"]))
    monkeypatch.setattr(transcript, "transscript_url", lambda url: pytest.fail("should not use whisper"))
    assert get_transcript("https://youtu.be/dQw4w9WgXcQ") == "hello world"


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
