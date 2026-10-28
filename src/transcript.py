from contextlib import nullcontext
from youtube_transcript_api import YoutubeTranscriptApi,NoTranscriptFound
import yt_dlp
from faster_whisper import WhisperModel
import re
import tempfile , os

_model = None
def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("small")
    return _model

def get_video_id(url):
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    return match.group(1) if match else url

def transscript_url(url):
    with tempfile.TemporaryDirectory() as tmp:
        opts = {
            "format": "bestaudio",
            "outtmpl": os.path.join(tmp, "audio.%(ext)s"),
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url,download=True)
            path = ydl.prepare_filename(info)
        segments, _ = get_model.transcribe(path)
        return " ".join(seg.text for seg in segments)

def youtubeTranscrip(str: url) -> str:
    ytt = YoutubeTranscriptApi()
    tyid = get_video_id(url)
    #try to see if the youtube transscript api could get the transscript
    try:
        transscript  = ytt.fetch( tyid , languages =["en"])
        test = " ".join(snippet.text for snippet in transscript)
    except CouldNotRetrieveTranscript:
        transscript = transscript_url(url)
    return transscript or None

if __name__ == "__main__" 
    import sys
    print(youtubeTranscrip(sys.argv[1]))



