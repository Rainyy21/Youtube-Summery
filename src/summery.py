import os
import re
from dotenv import load_dotenv
from transcript import clean_transcript, chunk_text
from concurrent.futures import ThreadPoolExecutor
from openai import (
    OpenAI,
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    APIStatusError,
)

TIMESTAMP = re.compile(r"\[(\d{1,2}(?::\d{2}){1,2})\](?!\()")
# "[32:05, 37:23]" -> split into "[32:05] [37:23]" so each one gets a link
PAIRED = re.compile(r"\[(\d{1,2}(?::\d{2}){1,2}(?:,\s*\d{1,2}(?::\d{2}){1,2})+)\]")
MAX_WORKERS = 4  # parts sent to the model at the same time

load_dotenv()

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    raise SystemExit(
        "OPENROUTER_API_KEY is not set. Add your OpenRouter key and try again."
    )

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

PROVIDER = [
    {
        "name": "Nemotron 3 Ultra (free)",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "on": True,
        "reasoning": {"enabled": False},
    },
    {
        "name": "GLM 5.3 Flash",
        "model": "z-ai/glm-5.3-flash",
        "on": True,
        # GLM can't turn reasoning off, so use the lowest effort it allows
        "reasoning": {"effort": "low"},
    },
]

CHUNK_SYSTEM = """You take notes on one section of a longer transcript.
Each transcript line starts with its timestamp, like [12:34].
List the main points as short bullets. Only output the bullets.
Keep the useful specifics: numbers, steps, names, commands.
End each bullet with one timestamp copied from the line where it's
discussed, like [12:34]. Never make one up."""

SYSTEM_PROMPT = """
    You summarize YouTube transcripts into Markdown notes.
    Always use this structure:
    Tags: (3-6 short lowercase topic tags, comma separated)
    ## Summary
    (4-6 sentences: what the video is about, the main argument or goal,
    and how it ends or what it concludes)
    ## Key Points
    (group the points under ### subheadings, one per main topic or section
    of the video. Under each, 2-5 bullets. Each bullet is 1-2 sentences and
    keeps the useful specifics: numbers, steps, names, examples, reasons.)
    ## Takeaways
    (3-5 bullets: what the viewer should remember or do)

    Rules for length:
    - Match the depth to the video. A short or simple video gets fewer
      sections and bullets; don't pad it out.
    - Never go over 2 sentences in a bullet.
    - No nested bullets or numbered lists; keep every bullet at one level.
    - Stay under about 700 words in total.
    - Skip filler like intros, sponsor segments, and "like and subscribe".

    Rules for timestamps:
    - The input has timestamps like [12:34] at the start of its lines.
    - Every Key Points bullet must end with one timestamp in brackets,
      copied from the input where that point is discussed, like [12:34].
    - One timestamp per bracket. Never make one up.
    - Don't put timestamps in the Summary or Takeaways.

    Only output the Markdown. Don't add an intro or closing line.
    """


# this will be what interact with the ai model
def call(client, model, prompt, system=SYSTEM_PROMPT, reasoning=None):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        extra_body={"reasoning": reasoning} if reasoning else None,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("model returned an empty response")
    return content


# this will try each model in PROVIDER in order until one works
def ask(prompt, system=SYSTEM_PROMPT):
    for p in PROVIDER:
        if not p["on"]:
            continue
        try:
            return call(openrouter, p["model"], prompt, system, p.get("reasoning"))
        except RateLimitError:
            # rate limits are temporary, so don't turn the model off
            print(f"{p['name']} limit reached, trying the next model.")
            continue
        except (AuthenticationError, APIConnectionError):
            print(f"{p['name']} unavailable, trying the next model.")
        except APIStatusError as e:
            print(f"{p['name']} error ({e.status_code}), trying the next model.")
        except ValueError:
            print(f"{p['name']} returned nothing, trying the next model.")
            continue
        p["on"] = False
    raise SystemExit(
        "All models failed. Check your internet, OpenRouter key, and credits."
    )


def clean_tag(tag):
    """Turn 'Machine Learning' or '#AI' into 'machine-learning' / 'ai'."""
    tag = tag.strip().lstrip("#").lower()
    tag = re.sub(r"\s+", "-", tag)
    return re.sub(r"[^\w-]", "", tag)


# pull the "Tags:" line out of the reply so it doesn't end up in the note
def split_tags(reply):
    tags = []
    kept = []
    for line in reply.strip().splitlines():
        if not tags and line.strip().lower().startswith("tags:"):
            raw = line.split(":", 1)[1]
            tags = [t for t in (clean_tag(t) for t in raw.split(",")) if t]
        else:
            kept.append(line)
    return "\n".join(kept).strip(), tags


def parse_time(text):
    """'12:34' → 754, '1:02:05' → 3725. Reverse of stamp() in transcript.py."""
    total = 0
    split_text = text.split(":")

    for time in split_text:
        total = total * 60 + int(time)
    return total


def link_timestamps(text, video_id, duration=None):
    """Turn [12:34] into [12:34](https://youtu.be/ID?t=754).
    Times past duration (in seconds) are left as plain text."""
    text = PAIRED.sub(
        lambda m: " ".join(f"[{t.strip()}]" for t in m.group(1).split(",")), text
    )

    def to_link(match):
        time_text = match.group(1)
        second = parse_time(time_text)

        if duration is not None and second > duration:
            return match.group(0)
        return f"[{time_text}](https://youtu.be/{video_id}?t={second})"

    return TIMESTAMP.sub(to_link, text)


def summarize(text):
    """Return (summary, tags). tags is empty if the model didn't give any.
    Long transcripts are noted chunk by chunk, then the notes are summarized."""
    chunks = chunk_text(clean_transcript(text))
    if len(chunks) == 1:
        return split_tags(ask(f"Transcript:\n{chunks[0]}"))

    def summary_chunk(numbered_chunk):
        i, chunk = numbered_chunk
        print(f"Summarizing part {i}/{len(chunks)}...")
        return ask(f"Part {i} of {len(chunks)}:\n{chunk}", CHUNK_SYSTEM)

    # map() keeps the notes in the same order as the chunks
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        notes = list(pool.map(summary_chunk, enumerate(chunks, 1)))

    combined = "Notes from each section of the video:\n\n" + "\n\n".join(notes)
    return split_tags(ask(combined))
