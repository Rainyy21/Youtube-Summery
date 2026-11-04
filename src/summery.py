import os
import re
from dotenv import load_dotenv
from openai import (
    OpenAI,
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    APIStatusError,
)

load_dotenv()

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    raise SystemExit("OPENROUTER_API_KEY is not set. Add your OpenRouter key and try again.")

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

PROVIDER = [
    {"name": "Nemotron 3 Ultra (free)", "model": "nvidia/nemotron-3-ultra-550b-a55b:free", "on": True},
    {"name": "GLM 5.3 Flash", "model": "z-ai/glm-5.3-flash", "on": True},
]

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
    - Stay under about 700 words in total.
    - Skip filler like intros, sponsor segments, and "like and subscribe".
    Only output the Markdown. Don't add an intro or closing line.
    """


# this will be what interact with the ai model
def call(client, model, prompt, system=SYSTEM_PROMPT):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
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
            return call(openrouter, p["model"], prompt, system)
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


def summarize(text):
    """Return (summary, tags). tags is empty if the model didn't give any."""
    return split_tags(ask(f"Transcript:\n{text}"))
