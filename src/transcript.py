from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
import yt_dlp
from faster_whisper import WhisperModel
import re
import tempfile, os
import html


_model = None

# filter
NOISE_TAGS = re.compile(r"\[[A-Za-z][A-Za-z ]*\]")  # [Music], not [12:34]
FILLERS = re.compile(r"\b(?:u+m+|u+h+|e+r+m+|h+m+)\b,?\s*", re.IGNORECASE)
REPEATS = re.compile(r"\b(\w+)(?:\s+\1\b)+", re.IGNORECASE)

# the chunk size
CHUNK_CHARS = 100_000  # most videos fit in one chunk; set small (e.g. 2000) to test


def stamp(seconds):
    """Turn 75.3 into '[1:15]', or '[1:02:05]' past an hour."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"[{h}:{m:02d}:{s:02d}]" if h else f"[{m}:{s:02d}]"


def with_stamps(parts):
    """One line per (start, text) pair, each starting with its timestamp."""
    return "\n".join(
        f"{stamp(start)} {text.strip()}" for start, text in parts if text.strip()
    )


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("small")
    return _model


# get the video id
def get_video_id(url: str):
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    return match.group(1) if match else url


# get the title for the videos
def get_title(url: str) -> str:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info.get("title") or ""
    except yt_dlp.utils.DownloadError:
        return ""


# get the transcript either form api or the yt_dlp and
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
        return with_stamps((seg.start, seg.text) for seg in segments)


def clean_transcript(transcript: str):
    """Remove caption noise to cut tokens. Keeps newlines and [m:ss] markers."""
    transcript = html.unescape(transcript)
    transcript = transcript.replace(">>", " ")
    transcript = NOISE_TAGS.sub(" ", transcript)
    transcript = FILLERS.sub("", transcript)
    transcript = REPEATS.sub(r"\1", transcript)
    transcript = re.sub(r"\s+([,.!?])", r"\1", transcript)
    transcript = re.sub(r",\s*,", ",", transcript)
    transcript = re.sub(r"[ \t]+", " ", transcript)
    lines = [line.strip() for line in transcript.splitlines()]
    return "\n".join(line for line in lines if line)


def split_units(text):
    """Break text into pieces that are safe to cut between.
    Returns (units, separator to rejoin them with)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines, "\n"

    sentence = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentence) > 1:
        return sentence, " "
    return text.split(), " "


def pack(units, max_chars, sep):
    """Group units into chunks no longer than max_chars."""
    chunks = []  # finished chunks
    current = []  # units in the chunk being filled
    size = 0  # characters in the current chunk

    for unit in units:
        cost = len(unit) + len(sep) if current else len(unit)
        if current and size + cost > max_chars:
            chunks.append(sep.join(current))
            current = []
            size = 0
            cost = len(unit)  # no separator at the start of a new chunk

        size += cost
        current.append(unit)

    if current:
        chunks.append(sep.join(current))

    return chunks


def chunk_text(text, max_chars=CHUNK_CHARS):
    """Split text into chunks, or return [text] if it already fits."""
    text = text.strip()

    if len(text) <= max_chars:
        return [text]

    # get units and separator from split_units
    units, sep = split_units(text)
    pieces = []
    for unit in units:
        if len(unit) > max_chars:
            pieces.extend(pack(unit.split(), max_chars, " "))
        else:
            pieces.append(unit)

    # pack pieces with the separator and return the result
    return pack(pieces, max_chars, sep)


def get_transcript(url: str) -> str | None:
    ytt = YouTubeTranscriptApi()
    tyid = get_video_id(url)
    # try to see if the youtube transscript api could get the transscript
    try:
        fetched = ytt.fetch(tyid, languages=["en"])
        text = with_stamps((snippet.start, snippet.text) for snippet in fetched)
    except CouldNotRetrieveTranscript:
        try:
            text = transscript_url(url)
        except yt_dlp.utils.DownloadError:
            return None
    return text or None


if __name__ == "__main__":
    import sys

    print(get_transcript(sys.argv[1]))
