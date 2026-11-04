from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, RateLimitError

import summery
from summery import clean_tag, split_tags


@pytest.fixture(autouse=True)
def reset_providers(monkeypatch):
    # ask() turns models off; give each test a fresh copy
    monkeypatch.setattr(summery, "PROVIDER", [dict(p) for p in summery.PROVIDER])


REQUEST = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")


def status_error(cls, code):
    return cls("err", response=httpx.Response(code, request=REQUEST), body=None)


def fake_client(content):
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    create = lambda **kwargs: reply
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Machine Learning", "machine-learning"),
        ("#AI", "ai"),
        ("  Python  ", "python"),
        ("c++!", "c"),
    ],
)
def test_clean_tag(raw, expected):
    assert clean_tag(raw) == expected


def test_split_tags():
    reply = "Tags: AI, Machine Learning, #python\n## Summary\nText here."
    body, tags = split_tags(reply)
    assert tags == ["ai", "machine-learning", "python"]
    assert body == "## Summary\nText here."


def test_split_tags_without_tags_line():
    body, tags = split_tags("## Summary\nText")
    assert tags == []
    assert body == "## Summary\nText"


def test_split_tags_only_uses_first_tags_line():
    body, tags = split_tags("Tags: a\nTags: b\nbody")
    assert tags == ["a"]
    assert "Tags: b" in body


def test_call_returns_content():
    assert summery.call(fake_client("hi"), "model", "prompt") == "hi"


def test_call_empty_raises():
    with pytest.raises(ValueError):
        summery.call(fake_client(""), "model", "prompt")


def test_ask_uses_first_model(monkeypatch):
    used = []
    monkeypatch.setattr(summery, "call", lambda c, model, p, s: used.append(model) or "ok")
    assert summery.ask("prompt") == "ok"
    assert used == [summery.PROVIDER[0]["model"]]


def test_ask_rate_limit_tries_next_but_keeps_model_on(monkeypatch):
    def call(client, model, prompt, system):
        if model == summery.PROVIDER[0]["model"]:
            raise status_error(RateLimitError, 429)
        return "second"

    monkeypatch.setattr(summery, "call", call)
    assert summery.ask("prompt") == "second"
    assert summery.PROVIDER[0]["on"] is True


@pytest.mark.parametrize(
    "error, stays_on",
    [
        (APIConnectionError(request=REQUEST), False),
        (status_error(APIStatusError, 500), False),
        (ValueError("empty"), True),  # empty reply might just be a fluke
    ],
)
def test_ask_other_errors_try_next_model(monkeypatch, error, stays_on):
    def call(client, model, prompt, system):
        if model == summery.PROVIDER[0]["model"]:
            raise error
        return "second"

    monkeypatch.setattr(summery, "call", call)
    assert summery.ask("prompt") == "second"
    assert summery.PROVIDER[0]["on"] is stays_on


def test_ask_skips_models_that_are_off(monkeypatch):
    summery.PROVIDER[0]["on"] = False
    used = []
    monkeypatch.setattr(summery, "call", lambda c, model, p, s: used.append(model) or "ok")
    summery.ask("prompt")
    assert used == [summery.PROVIDER[1]["model"]]


def test_ask_all_fail_exits(monkeypatch):
    def call(*args):
        raise status_error(APIStatusError, 500)

    monkeypatch.setattr(summery, "call", call)
    with pytest.raises(SystemExit):
        summery.ask("prompt")


def test_summarize(monkeypatch):
    monkeypatch.setattr(summery, "ask", lambda prompt: "Tags: ai\n## Summary\nhi")
    assert summery.summarize("transcript") == ("## Summary\nhi", ["ai"])
