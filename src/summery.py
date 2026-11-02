import os
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
    {"name": "GLM 5.2 (free)", "model": "z-ai/glm-5.2:free", "on": True},
    {"name": "GLM 5.3 Flash", "model": "z-ai/glm-5.3-flash", "on": True},
]

SYSTEM_PROMPT = """
    You summarize YouTube transcripts into Markdown notes.
    Always use this structure:
    ## Summary
    (3-5 sentences)
    ## Key Points
    (bullet list)
    ## Takeaways
    (bullet list)
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


def summarize(text):
    return ask(f"Transcript:\n{text}")
