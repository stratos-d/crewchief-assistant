import pytest

import src.router as router


class FakeClient:
    """Stands in for the OpenAI client and records the request."""

    def __init__(self, content):
        self.kwargs = None
        outer = self

        class Completions:
            def create(self, **kwargs):
                outer.kwargs = kwargs
                message = type("Message", (), {"content": content})
                choice = type("Choice", (), {"message": message})
                return type("Response", (), {"choices": [choice]})

        self.chat = type("Chat", (), {"completions": Completions()})()


def route(monkeypatch, content, commands, text="box this lap"):
    client = FakeClient(content)
    monkeypatch.setattr(router, "get_openai_client", lambda: client)
    monkeypatch.setattr(router, "get_all_commands", lambda: commands)
    return router.get_intent(text), client


def test_valid_intent_and_schema(monkeypatch):
    result, client = route(monkeypatch, '{"intent": "pit request", "confidence": 90}', ["pit request", "fuel report"])
    assert result == {"intent": "pit request", "confidence": 90, "exact": False}
    schema = client.kwargs["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["intent"]["enum"] == ["pit request", "fuel report", "unknown"]
    assert "unknown" in client.kwargs["messages"][0]["content"]


def test_unlisted_intent_becomes_unknown(monkeypatch):
    result, _ = route(monkeypatch, '{"intent": "Pit Request", "confidence": 95}', ["pit request"])
    assert result["intent"] == "unknown"


def test_string_confidence_is_coerced(monkeypatch):
    result, _ = route(monkeypatch, '{"intent": "pit request", "confidence": "85"}', ["pit request"])
    assert result["confidence"] == 85


def test_null_fields_become_unknown(monkeypatch):
    result, _ = route(monkeypatch, '{"intent": null, "confidence": null}', ["pit request"])
    assert result == {"intent": "unknown", "confidence": 0, "exact": False}


def test_enum_is_deduplicated(monkeypatch):
    _, client = route(monkeypatch, '{"intent": "a", "confidence": 1}', ["a", "a", "unknown", "b"])
    assert client.kwargs["response_format"]["json_schema"]["schema"]["properties"]["intent"]["enum"] == ["a", "b", "unknown"]


def test_exact_command_name_skips_the_api(monkeypatch):
    result, client = route(monkeypatch, "{}", ["whats my gap behind", "hows my fuel"], text="How’s my fuel?")
    assert result == {"intent": "hows my fuel", "confidence": 100, "exact": True}
    assert client.kwargs is None


def test_api_errors_propagate(monkeypatch):
    class Broken:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("401 invalid api key")

    monkeypatch.setattr(router, "get_openai_client", lambda: Broken)
    monkeypatch.setattr(router, "get_all_commands", lambda: ["pit request"])
    with pytest.raises(RuntimeError):
        router.get_intent("box this lap")
