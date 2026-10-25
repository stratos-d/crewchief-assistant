import threading
import time

import pytest

import src.ui.engine as engine_mod
from src.audio import Clip

SPOKEN = Clip(wav=None, seconds=1.5)


class FakeMic:
    def close(self):
        pass


@pytest.fixture
def engine(monkeypatch):
    """Engine wired to fakes; collects statuses, results and not-understood beeps."""
    seen = {"status": [], "result": [], "beeps": 0}
    monkeypatch.setattr(engine_mod, "Microphone", FakeMic)
    monkeypatch.setattr(engine_mod, "get_setting", lambda key, default=None: 50)
    monkeypatch.setattr(engine_mod, "play_not_understood", lambda: seen.__setitem__("beeps", seen["beeps"] + 1))

    def on_event(kind, **data):
        seen[kind].append(data.get("state") or data.get("result"))

    eng = engine_mod.VoiceEngine(on_event=on_event)
    yield eng, seen
    eng.stop()


def wait_for(condition, seconds=6):
    deadline = time.time() + seconds
    while not condition() and time.time() < deadline:
        time.sleep(0.02)
    return condition()


def test_loop_survives_errors(engine, monkeypatch):
    eng, seen = engine
    calls, pressed = {"n": 0}, []

    def fake_record(mic, ptt_key, stop_event, on_start=None, on_stop=None):
        calls["n"] += 1
        if calls["n"] > 3:
            stop_event.wait(5)
            return None
        on_start()
        on_stop()
        return SPOKEN

    def fake_trigger(intent):
        if not pressed:
            pressed.append("boom")
            raise RuntimeError("Failed to acquire vJoy device")
        pressed.append(intent)
        return 7

    intents = iter([{"intent": "pit request", "confidence": 90}, {"intent": None, "confidence": None},
                    {"intent": "pit request", "confidence": 90}])
    monkeypatch.setattr(engine_mod, "record_command", fake_record)
    monkeypatch.setattr(engine_mod, "transcribe_audio", lambda buf: "box box")
    monkeypatch.setattr(engine_mod, "get_intent", lambda text: next(intents))
    monkeypatch.setattr(engine_mod, "trigger_action", fake_trigger)

    eng.start("f8")
    assert wait_for(lambda: calls["n"] >= 4)
    assert "error" in seen["status"]
    assert pressed == ["boom", "pit request"]
    assert seen["result"][-1].outcome == "pressed"


def test_stop_then_start_does_not_run_two_loops(engine, monkeypatch):
    eng, _ = engine
    release_api, lock = threading.Event(), threading.Lock()
    active, pressed, first = {"now": 0, "max": 0}, [], {"done": False}

    def fake_record(mic, ptt_key, stop_event, on_start=None, on_stop=None):
        with lock:
            active["now"] += 1
            active["max"] = max(active["max"], active["now"])
        try:
            if not first["done"]:
                first["done"] = True
                return SPOKEN
            stop_event.wait(0.3)
            return None
        finally:
            with lock:
                active["now"] -= 1

    def slow_transcribe(buf):
        release_api.wait(5)
        return "box box"

    monkeypatch.setattr(engine_mod, "record_command", fake_record)
    monkeypatch.setattr(engine_mod, "transcribe_audio", slow_transcribe)
    monkeypatch.setattr(engine_mod, "get_intent", lambda text: {"intent": "pit request", "confidence": 90})
    monkeypatch.setattr(engine_mod, "trigger_action", lambda intent: pressed.append(intent))

    eng.start("f8")
    time.sleep(0.2)   # first run is waiting on the API
    eng.stop()
    eng.start("f8")   # STOP then START while processing
    time.sleep(0.2)
    release_api.set()
    time.sleep(1.0)
    assert pressed == []
    assert active["max"] == 1


@pytest.mark.parametrize("intent, confidence, button, outcome, beeps", [
    ("pit request", 90, 31, "pressed", 0),
    ("unknown", 0, None, "unknown", 1),
    ("pit request", 20, None, "low_confidence", 1),
    ("pit request", 90, None, "no_binding", 1),
])
def test_outcomes_and_not_understood_beep(engine, monkeypatch, intent, confidence, button, outcome, beeps):
    eng, seen = engine
    first = {"done": False}

    def fake_record(mic, ptt_key, stop_event, on_start=None, on_stop=None):
        if first["done"]:
            stop_event.wait(5)
            return None
        first["done"] = True
        on_start()
        on_stop()
        return SPOKEN

    monkeypatch.setattr(engine_mod, "record_command", fake_record)
    monkeypatch.setattr(engine_mod, "transcribe_audio", lambda buf: "box this lap")
    monkeypatch.setattr(engine_mod, "get_intent", lambda text: {"intent": intent, "confidence": confidence})
    monkeypatch.setattr(engine_mod, "trigger_action", lambda name: button)

    eng.start("f8")
    assert wait_for(lambda: seen["result"])
    assert seen["result"][0].outcome == outcome
    assert seen["beeps"] == beeps


def test_friendly_errors():
    AuthenticationError = type("AuthenticationError", (Exception,), {})
    PortAudioError = type("PortAudioError", (Exception,), {})
    assert engine_mod.friendly_error(AuthenticationError("401")) == "Invalid OpenAI API key."
    assert engine_mod.friendly_error(PortAudioError("-9996")) == "Microphone not available."
    assert "Settings" in engine_mod.friendly_error(ValueError("OpenAI API key not configured. Set it"))


def test_echoed_hint_list_is_not_understood(engine, monkeypatch):
    clip, transcript = Clip(wav=None, seconds=4.0), "volume up, volume down, get car status, " * 20
    eng, seen = engine
    first, sent = {"done": False}, []

    def fake_record(mic, ptt_key, stop_event, on_start=None, on_stop=None):
        if first["done"]:
            stop_event.wait(5)
            return None
        first["done"] = True
        return clip

    monkeypatch.setattr(engine_mod, "record_command", fake_record)
    monkeypatch.setattr(engine_mod, "transcribe_audio", lambda wav: sent.append(wav) or transcript)
    monkeypatch.setattr(engine_mod, "get_intent", lambda text: pytest.fail("router called"))

    eng.start("f8")
    assert wait_for(lambda: seen["result"])
    assert seen["result"][0].outcome == "no_speech"
    assert seen["beeps"] == 1
    assert len(sent) == 1
