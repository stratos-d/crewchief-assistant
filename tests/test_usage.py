import json

import pytest

import src.router as router
import src.usage as usage

# What the API reports for a 4 s clip with the command list as the prompt, and for one router call
TRANSCRIPTION = {"input_tokens": 338, "output_tokens": 12, "input_token_details": {"audio_tokens": 43, "text_tokens": 295}}
CHAT = {"prompt_tokens": 774, "completion_tokens": 12}


def test_transcription_cost_prices_audio_and_text_separately():
    tokens, dollars = usage.cost_of("gpt-4o-mini-transcribe", TRANSCRIPTION)
    assert tokens == 350
    assert dollars == pytest.approx((295 * 1.25 + 43 * 3.00 + 12 * 5.00) / 1e6)


def test_router_cost():
    tokens, dollars = usage.cost_of("gpt-4o-mini", CHAT)
    assert tokens == 786
    assert dollars == pytest.approx((774 * 0.15 + 12 * 0.60) / 1e6)


def test_whisper_is_priced_by_the_minute():
    _, dollars = usage.cost_of("whisper-1", {"type": "duration", "seconds": 30})
    assert dollars == pytest.approx(0.003)


def test_unknown_model_is_counted_but_not_priced():
    usage.record("some-future-model", CHAT)
    month = usage.summary()["month"]
    assert month["tokens"] == 786 and month["unpriced"] == 786 and month["cost"] == 0


def test_a_command_adds_up_and_survives_a_restart():
    usage.record("gpt-4o-mini-transcribe", TRANSCRIPTION, command=True)
    usage.record("gpt-4o-mini", CHAT)
    usage.record("gpt-4o-mini-transcribe", None, command=True)  # a reply without usage still counts the command

    usage._data = None  # as if the app restarted
    month = usage.summary()["month"]
    assert month["commands"] == 2
    assert month["tokens"] == 350 + 786
    assert month["cost"] == pytest.approx(usage.cost_of("gpt-4o-mini-transcribe", TRANSCRIPTION)[1]
                                          + usage.cost_of("gpt-4o-mini", CHAT)[1])


def test_months_are_kept_apart(monkeypatch):
    monkeypatch.setattr(usage, "_month", lambda: "2026-09")
    usage.record("gpt-4o-mini", CHAT, command=True)
    monkeypatch.setattr(usage, "_month", lambda: "2026-10")
    usage.record("gpt-4o-mini", CHAT, command=True)
    totals = usage.summary()
    assert totals["month"]["commands"] == 1 and totals["total"]["commands"] == 2


def test_reset_and_unreadable_file():
    usage.record("gpt-4o-mini", CHAT, command=True)
    usage.reset()
    assert usage.summary()["total"]["commands"] == 0

    with open(usage.USAGE_PATH, "w", encoding="utf-8") as f:
        f.write("{not json")
    usage._data = None
    assert usage.summary()["total"] == {"commands": 0, "tokens": 0, "cost": 0.0, "unpriced": 0}


def test_router_records_its_usage(monkeypatch):
    class Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    message = type("Message", (), {"content": json.dumps({"intent": "hows my fuel", "confidence": 90})})
                    choice = type("Choice", (), {"message": message})
                    return type("Response", (), {"choices": [choice], "usage": CHAT})

    monkeypatch.setattr(router, "get_openai_client", lambda: Client)
    monkeypatch.setattr(router, "get_all_commands", lambda: ["hows my fuel"])
    router.get_intent("how much fuel have I got")
    assert usage.summary()["month"]["tokens"] == 786
