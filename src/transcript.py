from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
import yt_dlp
from faster_whisper import WhisperModel
import re
import tempfile, os

_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("small")
    return _model


def get_video_id(url: str):
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    return match.group(1) if match else url

def get_title(url: str) -> str:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info.get("title") or ""
    except yt_dlp.utils.DownloadError:
        return ""

def transscript_url(url: str):
    with tempfile.TemporaryDirectory() as tmp:
        opts = {
            "format": "bestaudio",
            "outtmpl": os.path.join(tmp, "audio.%(ext)s"),
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
        segments, _ = get_model().transcribe(path)
        return " ".join(seg.text for seg in segments)


def get_transcript(url: str) -> str | None:
    ytt = YouTubeTranscriptApi()
    tyid = get_video_id(url)
    # try to see if the youtube transscript api could get the transscript
    try:
        fetched = ytt.fetch(tyid, languages=["en"])
        text = " ".join(snippet.text for snippet in fetched)
    except CouldNotRetrieveTranscript:
        try:
            text = transscript_url(url)
        except yt_dlp.utils.DownloadError:
            return None
    return text or None


if __name__ == "__main__":
    import sys

    print(get_transcript(sys.argv[1]))
